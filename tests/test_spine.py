import asyncio
from dataclasses import replace
from kekw.config import Settings
from kekw.market.engine import MarketEngine
from kekw.store import Store
from kekw.models import ChatMessage

class Clock:
    t=1000.
    def __call__(self): return self.t

async def setup(tmp_path, clock=None):
    store=await Store(str(tmp_path/"test.db")).open(); settings=Settings(k1=.05,k2=.14)
    eng=MarketEngine(store,settings=settings,clock=clock or (lambda:1000.)); eng.stream_start=clock() if clock else 1000.
    await eng.initialize(); return store,eng

def test_chat_to_candle(tmp_path):
    async def run():
        clock=Clock(); store,eng=await setup(tmp_path,clock)
        for i in range(30):
            user=f"u{i%5}"
            text="KEKW KEKW KEKW" if i<10 else ("!buy $KEKW 10" if i==10 else "KEKW KEKW KEKW")
            await eng.on_message(ChatMessage(user,f"User {user}",text,tokens=("KEKW","KEKW","KEKW")))
            clock.t+=1
        listing=await store.listing("KEKW"); wallet=await store.wallet("u0")
        assert listing is not None and eng.candles_for("KEKW")
        assert eng.candles_for("KEKW")[-1].close>50
        assert wallet["balance"] < 100+10+10 # first trade bonus/founder can apply; order spent 10
        assert await store.ledger_count("u0")==3
        await store.close()
    asyncio.run(run())

def test_formula_clamp_and_cold_start(tmp_path):
    async def run():
        store,eng=await setup(tmp_path); await eng.batch(force=True)
        assert Settings().k2==0.14
        assert all(c.close>0 for c in eng.candles.values())
        assert all(abs(v)<=.25 for v in eng.price_delta.values())
        await store.close()
    asyncio.run(run())

def test_trade_rate_limit(tmp_path):
    async def run():
        clock=Clock(); store,eng=await setup(tmp_path,clock)
        assert await eng.trade("u","buy","KEKW",10)
        assert not await eng.trade("u","buy","KEKW",10)
        clock.t+=5
        assert await eng.trade("u","buy","KEKW",10)
        await store.close()
    asyncio.run(run())

def test_breaker_halts_listing(tmp_path):
    async def run():
        clock=Clock(); store,eng=await setup(tmp_path,clock)
        row=await store.listing("KEKW"); await store.set_price("KEKW",row["price"]*.79); eng.history["KEKW"].append((clock(),row["price"])); clock.t+=60
        eng.settings=replace(eng.settings,k1=0,k2=0)
        await eng.batch(force=True)
        assert (await store.listing("KEKW"))["halted"]
        await store.close()
    asyncio.run(run())

def test_passive_income_controlled_clock(tmp_path):
    async def run():
        clock=Clock(); clock.t=0; store,eng=await setup(tmp_path,clock)
        await eng.on_message(ChatMessage("earner","Earner","hello",tokens=()))
        clock.t=60; await eng.on_message(ChatMessage("earner","Earner","hello",tokens=()))
        assert (await store.wallet("earner"))["balance"]==101
        clock.t=1800; await eng.on_message(ChatMessage("earner","Earner","hello",tokens=()))
        assert (await store.wallet("earner"))["balance"]==120
        await store.close()
    asyncio.run(run())

def test_balance_reply_content():
    from kekw.main import format_balance, format_trade_reply
    assert format_balance("Ada",120)=="@Ada balance: 120.0T"
    assert format_trade_reply("Ada","!buy $KEKW 10",True)=="@Ada FILLED 10T $KEKW"
    assert format_trade_reply("Ada","!sell $KEKW 2",True)=="@Ada Sold 2 $KEKW"
    assert format_trade_reply("Ada","!buy $KEKW 10",False,"insufficient Tendies")=="@Ada insufficient Tendies"
    assert format_trade_reply("Ada","!buy $KEKW 10",False,"rate-limited")=="@Ada rate-limited"

def test_found_sanitization():
    from kekw.main import sanitize_found_ticker
    assert sanitize_found_ticker("PogChamp")=="POGCHAMP"
    assert sanitize_found_ticker("bad!!") is None

def test_trade_headline_throttle():
    from kekw.desk.headlines import HeadlineDesk
    desk=HeadlineDesk()
    assert desk.should_emit_trade(100)
    assert not desk.should_emit_trade(119.9)
    assert desk.should_emit_trade(120)

def test_positions_reload_after_restart(tmp_path):
    async def run():
        clock=Clock(); store,eng=await setup(tmp_path,clock)
        assert await eng.trade("persisted","buy","KEKW",10)
        expected=eng.positions["persisted","KEKW"]
        await store.close()
        store=await Store(str(tmp_path/"test.db")).open(); restarted=MarketEngine(store,settings=Settings(k1=.05,k2=.14),clock=clock)
        await restarted.initialize()
        assert restarted.positions["persisted","KEKW"]==expected
        await store.close()
    asyncio.run(run())
