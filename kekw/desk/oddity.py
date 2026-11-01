from enum import Enum
from ..events import MarketEvent

class OddityState(str,Enum):
    SASSY="SASSY"; PANIC="PANIC"; FREEZE="FREEZE"; SCREAMING="SCREAMING"; SULK="SULK"
class Oddity:
    def __init__(self,bus=None): self.state=OddityState.SASSY; self.bus=bus
    async def on_event(self,event):
        kind=event.kind if isinstance(event,MarketEvent) else str(event).upper()
        payload=event.payload if isinstance(event,MarketEvent) else {}
        key=kind.upper()
        if key=="VERDICT": state=OddityState.SCREAMING if str(payload.get("winner"," ")).upper().endswith("_NO") else OddityState.SASSY
        elif key=="TRADE" and float(payload.get("notional",0))>=25: state=OddityState.SASSY
        else: state={"HALTED":OddityState.PANIC,"CIRCUIT_BREAKER":OddityState.PANIC,"RED_KEY":OddityState.FREEZE,"FORCE_CRASH":OddityState.SCREAMING,"CONTRACT_NO_CRASH":OddityState.SCREAMING,"CONTRACT_YES_MOONS":OddityState.SASSY,"CONTRACT_SETTLED":OddityState.SASSY,"CLOSE_CARD":OddityState.SULK,"CLOSE":OddityState.SULK}.get(key,OddityState.SASSY)
        self.state=state
        if self.bus: await self.bus.publish(MarketEvent("oddity",{"state":state.value}))
        return state
    async def run(self,stop_event):
        if not self.bus: return
        queue=self.bus.subscribe(MarketEvent)
        while not stop_event.is_set():
            event_task=__import__("asyncio").create_task(queue.get())
            stop_task=__import__("asyncio").create_task(stop_event.wait())
            done,pending=await __import__("asyncio").wait((event_task,stop_task),return_when=__import__("asyncio").FIRST_COMPLETED)
            for task in pending: task.cancel()
            if stop_task in done: break
            event=event_task.result()
            if event.kind!="oddity": await self.on_event(event)
