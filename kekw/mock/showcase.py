import asyncio, json, tempfile
from pathlib import Path
from ..bus import EventBus
from ..config import Settings
from ..desk.headlines import HeadlineDesk
from ..desk.oddity import Oddity
from ..events import MarketEvent
from ..market.contracts import PrimeTime
from ..market.engine import MarketEngine
from ..sources.chat_source import FileAdapter
from ..store import Store

class Showcase:
    def __init__(self,bus,engine,desk=None,oddity=None,clock=None,prime=None):
        self.bus,self.engine=bus,engine; self.desk=desk or HeadlineDesk(bus=bus); self.oddity=oddity or Oddity(bus=bus)
        self._time=[(clock or (lambda:1000))()]; self.prime=prime or PrimeTime(bus=bus,clock=lambda:self._time[0],store=engine.store); self.emitted=[]
    async def _emit(self,kind,payload=None):
        event=MarketEvent(kind,payload or {}); await self.bus.publish(event); self.emitted.append(event)
        await self.oddity.on_event(event)
        if kind=="open": await self.desk.generate("open",event.payload)
        if kind in ("ipo","circuit_breaker","stage_breaking","contract_settled"):
            trigger="breaker" if kind=="circuit_breaker" else "ipo" if kind=="ipo" else "trade"
            await self.desk.generate(trigger,event.payload,user=event.payload.get("user","chat"),ticker=event.payload.get("ticker","KEKW"))
    async def run(self,timeline,base_dir=Path("."),beat_delay=0,advance_market_clock=None):
        source=FileAdapter(str(base_dir/timeline["message_file_relative"])); messages=[]
        async for message in source: messages.append(message)
        for beat in timeline["beats"]:
            await self._emit("stage_beat",{"id":beat["id"],"label":beat["label"]})
            if beat_delay: await asyncio.sleep(beat_delay)
            kind=beat["kind"]
            if kind=="ipo_flood":
                indices=beat.get("messages",range(len(messages)))
                for message_position,index in enumerate(indices):
                    msg=messages[index]
                    if advance_market_clock: advance_market_clock(5)
                    before={x["ticker"] for x in await self.engine.store.listings()}; await self.engine.on_message(msg)
                    after={x["ticker"] for x in await self.engine.store.listings()}
                    for ticker in sorted(after-before): await self._emit("ipo",{"ticker":ticker,"anchor":50,"prospectus":"Community discovered ticker."})
                    if beat_delay and message_position<len(indices)-1: await asyncio.sleep(beat_delay)
            elif kind=="named_kill":
                msg=messages[beat["message"]]
                if advance_market_clock: advance_market_clock(5)
                filled=await self.engine.on_message(msg)
                await self._emit("stage_breaking",{"user":msg.display_name,"ticker":"KEKW","text":msg.text,"filled":filled,"booth":msg.user_id.upper().replace("_","-") if msg.user_id.lower().startswith("booth_") else None})
            elif kind=="headline_prompt":
                await self.desk.prompt(beat["emote"]); await self._emit("headline_prompt",{"emote":beat["emote"]})
            elif kind=="stake_open":
                contract=await self.prime.open(beat["title"],60,is_mod=True); await self._emit("stake_open",{"id":contract.contract_id,"title":contract.title,"yes":contract.yes_ticker,"no":contract.no_ticker,"anchor":50})
                await self.prime.wager(contract.contract_id,"booth_01",contract.yes_ticker,10); await self.prime.wager(contract.contract_id,"booth_02",contract.no_ticker,5)
                timeline["_contract_id"]=contract.contract_id
            elif kind=="verdict":
                contract=self.prime.contracts[timeline["_contract_id"]]
                if advance_market_clock:
                    remaining=max(0,contract.closes_at-self.prime.clock())
                    if remaining: advance_market_clock(remaining)
                else:
                    self._time[0]=max(self._time[0],contract.closes_at)
                await self.prime.settle(timeline["_contract_id"],beat["winner"],settle_key=True); await self._emit("verdict",{"winner":beat["winner"]})
            else: await self._emit(kind,beat.get("payload",{}))
        return self.emitted

async def dry_run(path="kekw/mock/demos/stage_timeline.json"):
    timeline_path=Path(path).resolve(); timeline=json.loads(timeline_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temp:
        store=await Store(str(Path(temp)/"showcase.db")).open(); bus=EventBus(); engine=MarketEngine(store,bus=bus,settings=Settings()); await engine.initialize()
        try: return await Showcase(bus,engine).run(timeline,timeline_path.parent)
        finally: await store.close()

if __name__=="__main__":
    import asyncio
    for event in asyncio.run(dry_run()): print(f"{event.kind}: {event.payload}")
