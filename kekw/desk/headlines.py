import asyncio, json, re
from ..events import Headline
from ..events import MarketEvent

SCHEMA={"type":"object","additionalProperties":False,"properties":{"headlines":{"type":"array","items":{"type":"string","maxLength":90},"minItems":1,"maxItems":2},"analyst":{"type":"string","maxLength":90},"bias":{"type":"number","minimum":-1,"maximum":1}},"required":["headlines","analyst","bias"]}

class HeadlineDesk:
    def __init__(self,api_key="",bus=None,client=None,writer=None,on_failure=None):
        self.api_key,self.bus,self.client,self.writer,self.on_failure=api_key,bus,client,writer,on_failure
        self.current=Headline(("MARKET OPEN: Oddity calls the line again.",),"The tape is live; conviction remains questionable.",0.0,"open")
        self.templates={"interval":("TENDIES TAPE: volatility discovers a microphone.","Oddity remains bullish on Oddity."),"breaker":("CIRCUIT BREAKER: the ticker has entered witness protection.","Risk controls halted the slide; Oddity disputes the arithmetic."),"ipo":("NEW IPO: chat has priced in pure vibes.","A fresh ticker joins the board at the 50T anchor."),"trade":("BREAKING: {user} moved {ticker}; confidence remains unhedged.","The order is matched against the synthetic maker at the posted spread."),"prompt":("{ticker}: chat attention is the only fundamental.","The analyst sees a volatile social signal and no balance sheet."),"open":("MARKET OPEN: Oddity calls the line again.","The tape is live; conviction remains questionable.")}
        self.history=[]
        self._last_interval=0.0
    def fallback(self,trigger="interval",**data):
        template=self.templates.get(trigger,self.templates["interval"])
        try: return Headline((template[0].format(**data),),template[1].format(**data),0.0,trigger)
        except KeyError: return Headline((template[0],),template[1],0.0,trigger)
    async def generate(self,trigger="interval",market_state=None,**data):
        fallback=self.fallback(trigger,**data); result=fallback
        if self.client or self.api_key:
            try:
                if self.client is None:
                    from openai import AsyncOpenAI
                    self.client=AsyncOpenAI(api_key=self.api_key)
                response=await self.client.chat.completions.create(model="gpt-4.1-mini",messages=[{"role":"system","content":"Write tabloid finance headlines. Never price assets. Only name users present in recent_trades."},{"role":"user","content":json.dumps({"trigger":trigger,"state":market_state or {},"recent_trades":(market_state or {}).get("recent_trades",[])})}],response_format={"type":"json_schema","json_schema":{"name":"desk_wire","strict":True,"schema":SCHEMA}})
                obj=json.loads(response.choices[0].message.content); result=Headline(tuple(obj["headlines"]),obj["analyst"],float(obj["bias"]),trigger)
                if any(len(x)>90 for x in (*result.headlines,result.analyst)) or not -1<=result.bias<=1: raise ValueError("invalid schema output")
            except Exception:
                result=fallback
                if self.bus: await self.bus.publish(MarketEvent("transmission_lost",{"message":"OpenAI unavailable; template wire active."}))
                if self.on_failure:
                    callback=self.on_failure()
                    if asyncio.iscoroutine(callback): await callback
        self.current=result
        self.history.append(result); self.history=self.history[-40:]
        if self.bus: await self.bus.publish(result)
        if self.writer:
            for line in (*result.headlines,result.analyst): await self._type(line)
        return result
    async def _type(self,text):
        for char in text:
            ret=self.writer({"type":"typewriter","char":char})
            if asyncio.iscoroutine(ret): await ret
            await asyncio.sleep(.018)
    async def prompt(self,emote):
        ticker=re.sub(r"[^A-Za-z0-9_]","",emote).upper() or "EMOTE"
        return await self.generate("prompt",{"ticker":ticker},ticker=ticker)
    async def prospectus(self,ticker):
        ticker=ticker.upper()
        if not (self.client or self.api_key): return "Community discovered ticker."
        result=await self.generate("ipo",{"ticker":ticker},ticker=ticker)
        line=result.analyst.strip()
        if line==self.templates["ipo"][1]: return "Community discovered ticker."
        return line[:90] or "Community discovered ticker."
    async def run(self,market_state,*,interval=60,stop_event=None):
        """Emit every interval, clamped to the locked 45–90 second cadence."""
        import time
        interval=max(45,min(90,interval)); await self.generate("open",market_state); pending_trade=None
        queue=self.bus.subscribe(MarketEvent) if self.bus else None
        while not (stop_event and stop_event.is_set()):
            try:
                if queue:
                    event_task=asyncio.create_task(queue.get())
                    stop_task=asyncio.create_task(stop_event.wait()) if stop_event else None
                    waits=[event_task]+([stop_task] if stop_task else [])
                    done,pending=await asyncio.wait(waits,timeout=interval,return_when=asyncio.FIRST_COMPLETED)
                    for task in pending: task.cancel()
                    if stop_task and stop_task in done: break
                    if event_task in done:
                        event=event_task.result()
                        if event.kind in ("ipo","circuit_breaker","stage_breaking","trade"):
                            trigger="breaker" if event.kind=="circuit_breaker" else "ipo" if event.kind=="ipo" else "trade"
                            state=market_state() if callable(market_state) else market_state
                            if trigger=="trade" and not self.should_emit_trade(time.monotonic()): pending_trade=event.payload
                            else:
                                await self.generate(trigger,state,user=event.payload.get("user",event.payload.get("display_name","chat")),ticker=event.payload.get("ticker","KEKW"))
                        continue
                else:
                    if stop_event: await asyncio.wait_for(stop_event.wait(),timeout=interval)
                    else: await asyncio.sleep(interval)
            except asyncio.TimeoutError: pass
            if stop_event and stop_event.is_set(): break
            state=market_state() if callable(market_state) else market_state
            await self.generate("interval",state)
            if pending_trade:
                await self.generate("trade",state,user=pending_trade.get("user","chat"),ticker=pending_trade.get("ticker","KEKW")); pending_trade=None; self._last_trade_headline=time.monotonic()
    def should_emit_trade(self,now):
        last=getattr(self,"_last_trade_headline",-1e9)
        if now-last<20: return False
        self._last_trade_headline=now
        return True
