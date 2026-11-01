from dataclasses import dataclass, field
from collections import defaultdict
from ..events import MarketEvent

@dataclass
class Wager:
    user_id: str
    ticker: str
    tendies: float
    display_name: str = ""

@dataclass
class Stake:
    contract_id: str
    title: str
    yes_ticker: str
    no_ticker: str
    closes_at: float
    bets: list[Wager] = field(default_factory=list)
    settled: bool = False

class PrimeTime:
    def __init__(self,bus=None,clock=None,store=None):
        import time
        self.bus,self.clock,self.store=bus,clock or time.time,store; self.contracts={}; self._next=1; self.pending={}
    @property
    def active_contract(self):
        now=self.clock()
        return next((c for c in reversed(list(self.contracts.values())) if not c.settled and now<c.closes_at),None)
    async def open(self,title,window=60,*,is_mod=False):
        if not is_mod: raise PermissionError("/stake is moderator-only")
        cid=f"PT{self._next:03d}"; self._next+=1; safe="".join(ch for ch in title.upper() if ch.isalnum())[:12] or "DUEL"
        stake=Stake(cid,title,f"{safe}_YES",f"{safe}_NO",self.clock()+window); self.contracts[cid]=stake
        if self.store:
            await self.store.add_listing(stake.yes_ticker,"PRIME TIME YES contract.",50)
            await self.store.add_listing(stake.no_ticker,"PRIME TIME NO contract.",50)
        await self._emit("stake_open",{"id":cid,"title":title,"yes":stake.yes_ticker,"no":stake.no_ticker,"anchor":50,"closes_at":stake.closes_at}); return stake
    async def wager(self,contract_id,user_id,ticker,tendies,display_name=""):
        c=self.contracts[contract_id]
        if c.settled or self.clock()>=c.closes_at: raise ValueError("contract book is closed")
        ticker=ticker.upper()
        if ticker not in (c.yes_ticker,c.no_ticker): raise ValueError("unknown duel ticker")
        if tendies<=0: raise ValueError("wager must be positive")
        w=Wager(user_id,ticker,float(tendies),display_name); self.pending.setdefault(contract_id,[]).append(w)
        if self.store and not await self.store.debit(user_id,w.tendies,"contract_buy",ticker):
            self.pending[contract_id].pop()
            raise ValueError("insufficient Tendies")
        bets=[*c.bets,*self.pending[contract_id]]
        yes=sum(x.tendies for x in bets if x.ticker==c.yes_ticker); no=sum(x.tendies for x in bets if x.ticker==c.no_ticker)
        await self._emit("contract_order",{"id":contract_id,"ticker":ticker,"user_id":user_id,"tendies":w.tendies,"yes_tendies":yes,"no_tendies":no,"closes_at":c.closes_at})
        return w
    async def flush_orders(self,contract_id):
        batch=self.pending.pop(contract_id,[])
        if batch:
            self.contracts[contract_id].bets.extend(batch)
            await self._emit("contract_order_batch",{"id":contract_id,"orders":[{"user_id":w.user_id,"display_name":w.display_name,"ticker":w.ticker,"tendies":w.tendies} for w in batch],"batched":True})
        return batch
    @staticmethod
    def settlement_math(bets,yes_ticker,no_ticker,winner):
        winner=winner.upper()
        if winner not in (yes_ticker.upper(),no_ticker.upper()): raise ValueError("winner must be YES or NO ticker")
        payouts={}; losing=0.0
        for bet in bets:
            if bet.ticker.upper()==winner: payouts[bet.user_id]=payouts.get(bet.user_id,0)+bet.tendies*1.9
            else: losing+=bet.tendies
        return {"payouts":payouts,"losing_stake":losing,"burned":losing*.1,"winner":winner}
    async def settle(self,contract_id,winner,*,settle_key=False):
        if not settle_key: raise PermissionError("settlement requires dashboard settle key")
        c=self.contracts[contract_id]
        if c.settled: raise ValueError("already settled")
        if self.clock()<c.closes_at: raise ValueError("contract window is still open")
        await self.flush_orders(contract_id)
        result=self.settlement_math(c.bets,c.yes_ticker,c.no_ticker,winner); c.settled=True
        if self.store:
            await self.store.set_price(c.yes_ticker,95.0 if result["winner"]==c.yes_ticker else 0.0)
            await self.store.set_price(c.no_ticker,95.0 if result["winner"]==c.no_ticker else 0.0)
            for user_id,amount in result["payouts"].items(): await self.store.credit(user_id,amount,"contract_payout",result["winner"])
            if result["burned"]:
                await self._emit("contract_burn",{"id":contract_id,"amount":result["burned"]})
        winner_payouts={}
        for bet in c.bets:
            if bet.ticker.upper()==result["winner"]:
                payout=winner_payouts.setdefault(bet.user_id,{"user_id":bet.user_id,"display_name":bet.display_name or bet.user_id,"payout":0.0})
                payout["payout"]+=bet.tendies*1.9
                if bet.display_name:
                    payout["display_name"]=bet.display_name
        winners=list(winner_payouts.values())
        verdict_calls=[]
        if self.store and hasattr(self.store,"record_verdict_call"):
            stakes=defaultdict(lambda:{"yes":0.0,"no":0.0,"display_name":""})
            for bet in c.bets:
                side="yes" if bet.ticker.upper()==c.yes_ticker.upper() else "no"
                stakes[bet.user_id][side]+=bet.tendies
                if bet.display_name: stakes[bet.user_id]["display_name"]=bet.display_name
            winning_side="yes" if result["winner"].upper()==c.yes_ticker.upper() else "no"
            losing_side="no" if winning_side=="yes" else "yes"
            for user_id,stake in stakes.items():
                # A user's larger side is their call; hedged ties do not extend a streak.
                correct=stake[winning_side]>stake[losing_side]
                verdict_calls.append(await self.store.record_verdict_call(
                    user_id,contract_id,correct,stake["display_name"] or user_id
                ))
        await self._emit("contract_yes_moons" if result["winner"]==c.yes_ticker else "contract_no_crash",{"id":contract_id,**result,"winners":winners})
        await self._emit("contract_settled",{"id":contract_id,"winner":result["winner"],**result,"winners":winners,"verdict_calls":verdict_calls})
        callback=getattr(self,"on_settle",None)
        if callback: callback({"id":contract_id,"winner":result["winner"],"burned":result["burned"]})
        return result
    async def _emit(self,kind,payload):
        if self.bus: await self.bus.publish(MarketEvent(kind,payload))
