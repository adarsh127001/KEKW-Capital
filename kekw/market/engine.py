import asyncio, math, re, time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from ..models import ChatMessage
from ..events import MarketEvent
from .orders import parse_order

BLUE_CHIPS={"KEKW":"The market's premier laughter index.","GG":"A blue chip in decisive victories.","FAIL":"A contrarian basket of spectacular misses."}
@dataclass
class Candle:
    ticker:str; bucket:int; open:float; high:float; low:float; close:float; volume:float=0

class MarketEngine:
    def __init__(self,store,bus=None,settings=None,clock=time.time):
        self.store,self.bus,self.settings,self.clock=store,bus,settings,clock
        self.fast=defaultdict(float); self.slow=defaultdict(lambda:1.0); self.seen=defaultdict(int); self.token_times=defaultdict(deque); self.chat=[]; self.recent_trades=[]
        self.candles={}; self.user_trades={}; self.stream_earned=defaultdict(int); self.positions=defaultdict(float); self.price_delta={}; self.history=defaultdict(lambda:deque())
        self.last_batch=0; self.last_chat=clock(); self.counts=defaultdict(int); self.skew=defaultdict(float); self.breaker_flags=set(); self.soft_closed=False; self.emote_pat=re.compile(r"^[A-Z0-9_]{2,}$")
        self.messages_ingested=0; self.ingress_mode="showcase"
    async def initialize(self):
        self.stream_start=self.clock()
        for row in await self.store.positions(): self.positions[row["user_id"],row["ticker"]]=row["shares"]
        for row in await self.store.candles():
            opening,closing=float(row["open"]),float(row["close"])
            high=max(float(row["high"]),opening,closing); low=min(float(row["low"]),opening,closing)
            candle=Candle(row["ticker"],row["bucket"],opening,high,low,closing,row["volume"])
            self.candles[candle.ticker,candle.bucket]=candle
            if high!=row["high"] or low!=row["low"]: await self.store.upsert_candle(candle)
        for ticker,prospectus in BLUE_CHIPS.items():
            existed=await self.store.listing(ticker); await self.store.add_listing(ticker,prospectus,50)
            if not existed and self.bus: await self.bus.publish(MarketEvent("ipo",{"ticker":ticker,"anchor":50,"prospectus":prospectus}))
    async def list_ticker(self,ticker,prospectus="Community discovered ticker."):
        ticker=ticker.upper()
        if await self.store.listing(ticker): return False
        await self.store.add_listing(ticker,prospectus[:90] or "Community discovered ticker.",50)
        if self.bus: await self.bus.publish(MarketEvent("ipo",{"ticker":ticker,"anchor":50,"prospectus":prospectus[:90]}))
        return True
    async def note_ingress(self,msg:ChatMessage):
        self.last_chat=self.clock(); self.chat.append(msg.text); self.chat=self.chat[-40:]
        self.messages_ingested+=1
        if self.bus: await self.bus.publish(MarketEvent("ingress",{"mode":self.ingress_mode,"messages":self.messages_ingested,"utc":datetime.now(timezone.utc).isoformat(),"last_chat_seconds":0}))
    async def on_message(self,msg:ChatMessage,count_ingress=True):
        if count_ingress: await self.note_ingress(msg)
        await self.touch_user(msg.user_id)
        for token in msg.tokens:
            ticker=token.upper().lstrip('$')
            if not self.emote_pat.match(ticker): continue
            self.counts[ticker]+=1
            if self.counts[ticker]>=3 and not await self.store.listing(ticker):
                prospectus="Community discovered ticker."; await self.store.add_listing(ticker,prospectus,50)
                if self.bus: await self.bus.publish(MarketEvent("ipo",{"ticker":ticker,"anchor":50,"prospectus":prospectus}))
            if await self.store.listing(ticker): self.token_times[ticker].append(self.clock())
        order=parse_order(msg.text)
        if order:
            result=await self.trade(msg.user_id,*order,display_name=msg.display_name)
            await self.batch()
            return result
        await self.batch()
    async def touch_user(self,user_id):
        await self.store.wallet(user_id)
        minute=int(max(0,self.clock()-self.stream_start)//60)
        self.stream_earned[user_id]+=await self.store.record_earn(user_id,minute,self.stream_earned[user_id])
    async def trade(self,user_id,side,ticker,qty,display_name=None):
        self.last_trade_error=None
        listing=await self.store.listing(ticker)
        if not listing or listing["halted"]: self.last_trade_error="ticker unavailable"; return False
        now=self.clock()
        if now-self.user_trades.get(user_id,-1e9)<self.settings.trade_limit_seconds:self.last_trade_error="rate-limited"; return False
        w=await self.store.wallet(user_id); await self.store.first_trade(user_id); w=await self.store.wallet(user_id)
        if side=="buy":
            cost=float(qty)
            if w["balance"]<cost:self.last_trade_error="insufficient Tendies"; return False
            shares=cost/(listing["price"]*1.01)
            if not await self.store.debit(user_id,cost,"buy",ticker):return False
            self.positions[user_id,ticker]+=shares; self.skew[ticker]+=min(.25,shares/1000)
        else:
            available=self.positions[user_id,ticker]
            qty=available if qty is None else qty
            if qty<=0 or available<qty:self.last_trade_error="insufficient shares"; return False
            proceeds=qty*listing["price"]*.99
            self.positions[user_id,ticker]-=qty; await self.store.credit(user_id,proceeds,"sell",ticker)
            self.skew[ticker]-=min(.25,qty/1000)
        self.user_trades[user_id]=now
        founder=await self.store.founder(ticker,user_id)
        if founder: await self.store.credit(user_id,10,"founder",ticker)
        await self.store.set_position(user_id,ticker,self.positions[user_id,ticker])
        notional=cost if side=="buy" else proceeds
        trade_event={"user":display_name or user_id,"user_id":user_id,"ticker":ticker,"side":side,"quantity":qty,"notional":notional}
        self.recent_trades.append(trade_event); self.recent_trades=self.recent_trades[-40:]
        if self.bus: await self.bus.publish(MarketEvent("trade",trade_event))
        return True
    async def batch(self,force=False):
        now=self.clock()
        if not force and now-self.last_batch<1:return
        self.last_batch=now; published=[]
        for row in await self.store.listings():
            t=row["ticker"]; events=self.token_times[t]
            while events and events[0]<now-5: events.popleft()
            count=len(events); self.seen[t]=count; f=self.settings.ema_fast_alpha; s=self.settings.ema_slow_alpha
            self.fast[t]=f*count+(1-f)*self.fast[t]; self.slow[t]=s*count+(1-s)*self.slow[t]
            mom=max(.25,min(8.0,(self.fast[t]+.01)/max(.01,self.slow[t]+.01)))
            raw=max(-.25,min(.25,max(self.settings.k1_min,min(self.settings.k1_max,self.settings.k1))*math.log(mom)+max(self.settings.k2_min,min(self.settings.k2_max,self.settings.k2))*self.skew.get(t,0)))
            price=row["price"]*(1+raw); self.skew[t]=0
            bucket=int(now//self.settings.candle_bucket_seconds); key=(t,bucket)
            c=self.candles.get(key)
            if c is None: c=Candle(t,bucket,row["price"],max(row["price"],price),min(row["price"],price),price); self.candles[key]=c
            c.high=max(c.high,c.open,price); c.low=min(c.low,c.open,price); c.close=price
            c.volume+=count
            self.price_delta[t]=price/row["price"]-1
            hist=self.history[t]; hist.append((now,price))
            while hist and hist[0][0]<now-60:hist.popleft()
            if not row["halted"] and len(hist)>1 and price<=hist[0][1]*.8:
                await self.store.set_halted(t)
                self.breaker_flags.add(t)
                if self.bus: await self.bus.publish(MarketEvent("circuit_breaker",{"ticker":t,"price":price,"state":"HALTED"}))
            if now-self.last_chat>120 and not self.soft_closed:
                price*=.95; c.close=price; self.soft_closed=True
            await self.store.set_price(t,price)
            await self.store.upsert_candle(c)
            # The candle in self.candles is updated again on the next batch.
            # Publish an immutable-in-practice snapshot so queued subscribers
            # receive this batch's OHLC values instead of a later mutation.
            published.append(Candle(c.ticker,c.bucket,c.open,c.high,c.low,c.close,c.volume))
        if self.bus:
            for candle in published: await self.bus.publish(candle)
    async def run(self,source):
        await self.initialize()
        async for msg in source: await self.on_message(msg)
        await self.batch(force=True)
    def candles_for(self,ticker): return sorted((c for (t,_),c in self.candles.items() if t==ticker.upper().lstrip('$')),key=lambda c:c.bucket)
