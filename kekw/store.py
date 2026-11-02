import time
import sys

try:
    # Windows Python 3.10's Proactor loop can strand aiosqlite's worker future;
    # use the same async-shaped built-in SQLite adapter as the offline fallback.
    if sys.platform=="win32" and sys.version_info<(3,11): raise ModuleNotFoundError("Use sync SQLite adapter on Windows Python 3.10")
    import aiosqlite
except ModuleNotFoundError:  # built-in SQLite keeps offline showcase usable
    import sqlite3
    class _Cursor:
        def __init__(self, cursor): self.cursor=cursor
        async def fetchone(self): return self.cursor.fetchone()
        async def fetchall(self): return self.cursor.fetchall()
    class _Connection:
        def __init__(self, connection): self.connection=connection
        @property
        def row_factory(self): return self.connection.row_factory
        @row_factory.setter
        def row_factory(self, value): self.connection.row_factory=value
        async def execute(self,*args): return _Cursor(self.connection.execute(*args))
        async def executescript(self,*args): self.connection.executescript(*args)
        async def commit(self): self.connection.commit()
        async def close(self): self.connection.close()
    class aiosqlite:
        IntegrityError=sqlite3.IntegrityError
        Row=sqlite3.Row
        @staticmethod
        async def connect(path): return _Connection(sqlite3.connect(path))

class Store:
    def __init__(self, path): self.path = path; self.db = None
    async def open(self):
        self.db = await aiosqlite.connect(self.path); self.db.row_factory = aiosqlite.Row
        await self.db.executescript('''
        CREATE TABLE IF NOT EXISTS wallets(user_id TEXT PRIMARY KEY, balance REAL NOT NULL, earned INTEGER NOT NULL DEFAULT 0, first_trade INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL,kind TEXT NOT NULL,amount REAL NOT NULL,ticker TEXT,detail TEXT,created_at REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS listings(ticker TEXT PRIMARY KEY, price REAL NOT NULL, prospectus TEXT NOT NULL, created_at REAL NOT NULL, founder_count INTEGER NOT NULL DEFAULT 0, halted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS founders(ticker TEXT NOT NULL,user_id TEXT NOT NULL,PRIMARY KEY(ticker,user_id));
        CREATE TABLE IF NOT EXISTS positions(user_id TEXT NOT NULL,ticker TEXT NOT NULL,shares REAL NOT NULL,PRIMARY KEY(user_id,ticker));
        CREATE TABLE IF NOT EXISTS candles(ticker TEXT NOT NULL,bucket INTEGER NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,volume REAL NOT NULL,PRIMARY KEY(ticker,bucket));
        CREATE TABLE IF NOT EXISTS verdict_streaks(user_id TEXT PRIMARY KEY,display_name TEXT NOT NULL DEFAULT '',current_streak INTEGER NOT NULL DEFAULT 0,best_streak INTEGER NOT NULL DEFAULT 0,last_contract_id TEXT,updated_at REAL NOT NULL DEFAULT 0);
        ''')
        # Existing local databases may predate ledger timestamps.
        columns=await (await self.db.execute("PRAGMA table_info(ledger)")).fetchall()
        if not any(row["name"]=="created_at" for row in columns):
            await self.db.execute("ALTER TABLE ledger ADD COLUMN created_at REAL NOT NULL DEFAULT 0")
        await self.db.commit(); return self
    async def close(self):
        if self.db: await self.db.close(); self.db=None
    async def wallet(self, user_id):
        await self.db.execute("INSERT OR IGNORE INTO wallets(user_id,balance) VALUES (?,100)",(user_id,)); await self.db.commit()
        row=await (await self.db.execute("SELECT * FROM wallets WHERE user_id=?",(user_id,))).fetchone(); return dict(row)
    async def credit(self,user_id,amount,kind="credit",ticker=None):
        await self.wallet(user_id); await self.db.execute("UPDATE wallets SET balance=balance+? WHERE user_id=?",(amount,user_id)); await self._record_ledger(user_id,kind,amount,ticker); await self.db.commit()
    async def debit(self,user_id,amount,kind="trade",ticker=None,detail=None):
        w=await self.wallet(user_id)
        if w["balance"]+1e-9 < amount: return False
        await self.db.execute("UPDATE wallets SET balance=balance-? WHERE user_id=?",(amount,user_id)); await self._record_ledger(user_id,kind,-amount,ticker,detail); await self.db.commit(); return True
    async def _record_ledger(self,user_id,kind,amount,ticker=None,detail=None):
        await self.db.execute("INSERT INTO ledger(user_id,kind,amount,ticker,detail,created_at) VALUES (?,?,?,?,?,?)",(user_id,kind,amount,ticker,detail,time.time()))
    async def add_listing(self,ticker,prospectus,anchor=50):
        await self.db.execute("INSERT OR IGNORE INTO listings(ticker,price,prospectus,created_at) VALUES (?,?,?,strftime('%s','now'))",(ticker,anchor,prospectus)); await self.db.commit()
    async def listing(self,ticker):
        row=await (await self.db.execute("SELECT * FROM listings WHERE ticker=?",(ticker.upper().lstrip('$'),))).fetchone(); return dict(row) if row else None
    async def listings(self):
        rows=await (await self.db.execute("SELECT * FROM listings ORDER BY ticker")).fetchall(); return [dict(r) for r in rows]
    async def wallets(self):
        rows=await (await self.db.execute("SELECT * FROM wallets ORDER BY balance DESC")).fetchall(); return [dict(r) for r in rows]
    async def positions(self):
        rows=await (await self.db.execute("SELECT user_id,ticker,shares FROM positions")).fetchall(); return [dict(r) for r in rows]
    async def candles(self):
        rows=await (await self.db.execute("SELECT ticker,bucket,open,high,low,close,volume FROM candles ORDER BY ticker,bucket DESC")).fetchall()
        counts={}; result=[]
        for row in rows:
            ticker=row["ticker"]; counts[ticker]=counts.get(ticker,0)+1
            if counts[ticker]<=160: result.append(dict(row))
        return sorted(result,key=lambda row:(row["ticker"],row["bucket"]))
    async def upsert_candle(self,candle):
        await self.db.execute("INSERT INTO candles(ticker,bucket,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?) ON CONFLICT(ticker,bucket) DO UPDATE SET open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume",(candle.ticker,candle.bucket,candle.open,candle.high,candle.low,candle.close,candle.volume))
        await self.db.commit()
    async def top_pnl(self,limit=5):
        rows=await (await self.db.execute("SELECT user_id,COALESCE(SUM(amount),0) pnl FROM ledger GROUP BY user_id ORDER BY pnl DESC LIMIT ?",(limit,))).fetchall(); return [dict(r) for r in rows]
    async def best_trader_today(self,now=None):
        from datetime import datetime,timezone
        stamp=time.time() if now is None else float(now)
        start=datetime.fromtimestamp(stamp,timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        end=start+86400
        row=await (await self.db.execute("SELECT user_id,COALESCE(SUM(amount),0) pnl FROM ledger WHERE created_at>=? AND created_at<? AND kind IN ('buy','sell','contract_buy','contract_payout') GROUP BY user_id ORDER BY pnl DESC,user_id ASC LIMIT 1",(start,end))).fetchone()
        result=dict(row) if row else None
        if result: result["utc_date"]=datetime.fromtimestamp(start,timezone.utc).date().isoformat()
        return result
    async def record_verdict_call(self,user_id,contract_id,correct,display_name=""):
        row=await (await self.db.execute("SELECT display_name,current_streak,best_streak FROM verdict_streaks WHERE user_id=?",(user_id,))).fetchone()
        current=(int(row["current_streak"])+1 if correct else 0) if row else (1 if correct else 0)
        best=max(int(row["best_streak"]) if row else 0,current)
        await self.db.execute("INSERT INTO verdict_streaks(user_id,display_name,current_streak,best_streak,last_contract_id,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=CASE WHEN excluded.display_name!='' THEN excluded.display_name ELSE verdict_streaks.display_name END,current_streak=excluded.current_streak,best_streak=excluded.best_streak,last_contract_id=excluded.last_contract_id,updated_at=excluded.updated_at",(user_id,display_name,current,best,contract_id,time.time()))
        await self.db.commit()
        return {"user_id":user_id,"display_name":display_name or (row["display_name"] if row else user_id),"current_streak":current,"best_streak":best,"last_contract_id":contract_id}
    async def verdict_streak(self,user_id):
        row=await (await self.db.execute("SELECT user_id,display_name,current_streak,best_streak,last_contract_id,updated_at FROM verdict_streaks WHERE user_id=?",(user_id,))).fetchone()
        return dict(row) if row else {"user_id":user_id,"display_name":user_id,"current_streak":0,"best_streak":0,"last_contract_id":None}
    async def top_verdict_streaks(self,limit=5):
        rows=await (await self.db.execute("SELECT user_id,display_name,current_streak,best_streak,last_contract_id,updated_at FROM verdict_streaks WHERE best_streak>0 ORDER BY best_streak DESC,current_streak DESC,user_id ASC LIMIT ?",(limit,))).fetchall()
        return [dict(row) for row in rows]
    async def set_position(self,user_id,ticker,shares):
        await self.db.execute("INSERT INTO positions(user_id,ticker,shares) VALUES (?,?,?) ON CONFLICT(user_id,ticker) DO UPDATE SET shares=excluded.shares",(user_id,ticker,shares)); await self.db.commit()
    async def ledger_count(self,user_id): return (await (await self.db.execute("SELECT COUNT(*) n FROM ledger WHERE user_id=?",(user_id,))).fetchone())["n"]
    async def set_price(self,ticker,price): await self.db.execute("UPDATE listings SET price=? WHERE ticker=?",(price,ticker)); await self.db.commit()
    async def set_halted(self,ticker): await self.db.execute("UPDATE listings SET halted=1 WHERE ticker=?",(ticker,)); await self.db.commit()
    async def set_unhalted(self,ticker): await self.db.execute("UPDATE listings SET halted=0 WHERE ticker=?",(ticker,)); await self.db.commit()
    async def founder(self,ticker,user_id):
        row=await self.listing(ticker)
        if row["founder_count"]>=3:return False
        try: await self.db.execute("INSERT INTO founders(ticker,user_id) VALUES (?,?)",(ticker,user_id))
        except aiosqlite.IntegrityError:return False
        await self.db.execute("UPDATE listings SET founder_count=founder_count+1 WHERE ticker=?",(ticker,)); await self.db.commit(); return True
    async def first_trade(self,user_id):
        await self.wallet(user_id); row=await (await self.db.execute("SELECT first_trade FROM wallets WHERE user_id=?",(user_id,))).fetchone()
        if row[0]:return False
        await self.db.execute("UPDATE wallets SET first_trade=1,balance=balance+10 WHERE user_id=?",(user_id,)); await self._record_ledger(user_id,"first_trade_bonus",10); await self.db.commit(); return True
    async def record_earn(self,user_id,stream_minutes,earned_this_stream=0):
        await self.wallet(user_id)
        earn=max(0,min(stream_minutes-earned_this_stream,20-earned_this_stream))
        if earn:
            await self.db.execute("UPDATE wallets SET balance=balance+?,earned=earned+? WHERE user_id=?",(earn,earn,user_id)); await self._record_ledger(user_id,"passive_income",earn); await self.db.commit()
        return earn
