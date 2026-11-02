import argparse, asyncio, json, sys, tempfile, time
import re
from datetime import datetime, timezone
from collections import deque
from .config import Settings
from .store import Store
from .market.engine import MarketEngine
from .sources.chat_source import FileAdapter, IRCAdapter
from .bus import EventBus
from .desk.headlines import HeadlineDesk
from .market.contracts import PrimeTime
from .desk.oddity import Oddity
from pathlib import Path
from .cards.recap import best_trader_of_day_png, html_recap, market_close_png, oddity_holdings_png, portfolio_png, status_card
from .events import MarketEvent

def format_balance(display_name,balance): return f"@{display_name} balance: {balance:.1f}T"
def sanitize_found_ticker(value): return value.upper() if re.fullmatch(r"[A-Za-z0-9_]{2,}",value) else None
def format_trade_reply(display_name,command,filled,error=None):
    parts=command.split(); ticker=parts[1].lstrip("$").upper() if len(parts)>1 else "?"
    if not filled: return f"@{display_name} {error or 'trade rejected'}"
    if parts[0].lower()=="!buy": return f"@{display_name} FILLED {parts[-1]}T ${ticker}"
    return f"@{display_name} Sold {parts[-1]} ${ticker}"
async def publish_chat_reply(bus,source,display_name,text):
    await bus.publish(MarketEvent("chat_reply",{"text":text,"user":display_name}))
    if isinstance(source,IRCAdapter):
        try: await source.SendMessage(text)
        except Exception: pass

async def serve(args):
    settings=Settings.from_env()
    showcase_temp=tempfile.TemporaryDirectory(prefix="kekw-showcase-") if getattr(args,"showcase",False) else None
    showcase_time=[time.time()] if showcase_temp else None
    market_clock=(lambda:showcase_time[0]) if showcase_time is not None else time.time
    db_path=str(Path(showcase_temp.name)/"showcase.sqlite3") if showcase_temp else settings.db_path
    store=await Store(db_path).open(); bus=EventBus(); engine=MarketEngine(store,bus=bus,settings=settings,clock=market_clock); await engine.initialize()
    engine.ingress_mode="showcase" if getattr(args,"showcase",False) else args.source
    def transmission_card(): return status_card(Path("recaps/transmission-lost.png"),"TRANSMISSION LOST","AI headline service unavailable; guaranteed template headlines remain on the wire.")
    desk=HeadlineDesk(settings.openai_api_key,bus=bus,on_failure=transmission_card); oddity=Oddity(bus=bus); stop=asyncio.Event(); desk_task=None; oddity_task=None; server_task=None; server=None; first_client=None
    prime=PrimeTime(bus=bus,store=store,clock=market_clock)
    verdicts=deque(maxlen=10)
    prime.on_settle=lambda result: verdicts.append(f"{result['winner']} settled; {result['burned']:.1f}T burned")
    async def recap_snapshot():
        pnl=await store.top_pnl(5)
        names={trade.get("user_id"):trade.get("user") for trade in engine.recent_trades if trade.get("user_id") and trade.get("user")}
        headlines=[line for item in desk.history[-3:] for line in (*item.headlines,item.analyst)]
        top_pnl=[{"user_id":r["user_id"],"display_name":names.get(r["user_id"],r["user_id"]),"pnl":r["pnl"]} for r in pnl]
        best=await store.best_trader_today()
        streaks=await store.top_verdict_streaks(5)
        for row in streaks: row["display_name"]=row.get("display_name") or names.get(row["user_id"],row["user_id"])
        if best: best["display_name"]=names.get(best["user_id"],best["user_id"])
        listings=await store.listings()
        ticker=max(engine.price_delta,key=lambda t:abs(engine.price_delta[t])) if engine.price_delta else (listings[0]["ticker"] if listings else None)
        candles=engine.candles_for(ticker) if ticker else []
        # A one-bucket mover produces only a vertical OHLC whisker on the recap.
        # Prefer the first listed ticker with a real time series for that chart.
        if len(candles)<2:
            populated=[(row["ticker"],engine.candles_for(row["ticker"])) for row in listings]
            populated=[entry for entry in populated if len(entry[1])>=2]
            if populated:
                ticker,candles=max(populated,key=lambda entry:len(entry[1]))
        chart={"ticker":ticker,"buckets":[c.bucket for c in candles],"opens":[c.open for c in candles],"highs":[c.high for c in candles],"lows":[c.low for c in candles],"closes":[c.close for c in candles]}
        return {"chart":chart,"headlines":headlines,"verdicts":list(verdicts),"top_pnl":top_pnl,"best_trader":best,"verdict_streaks":streaks}
    async def render_portfolio_cards(snapshot,base):
        rows=snapshot.get("top_pnl",[])[:5]; listings={row["ticker"]:row for row in await store.listings()}; output=[]; used=set()
        for row in rows:
            user_id=str(row.get("user_id") or row.get("display_name") or "trader"); name=str(row.get("display_name") or user_id)
            slug=re.sub(r"[^A-Za-z0-9_-]+","_",name).strip("_") or "trader"
            if slug in used: slug=f"{slug}_{re.sub(r'[^A-Za-z0-9_-]+','_',user_id)}"
            used.add(slug)
            holdings=[(ticker,shares,shares*float(listings.get(ticker,{}).get("price",0))) for (owner,ticker),shares in engine.positions.items() if owner==user_id and shares>0]
            output.append(str(portfolio_png(base/"portfolios"/f"{slug}.png",name,holdings,float(row.get("pnl",0)),["Bold entry. The exit remains a mystery.","Someone call the line back.","Sell the rumor, lose the news.","The tape remembers.","Certified bagholder of the day."][hash(user_id)%5])))
        return output
    auto_recap_done=False
    async def write_recap(base):
        snapshot=await recap_snapshot()
        png=market_close_png(base/"market-close.png",snapshot); html=html_recap(base/"index.html",snapshot); oddity=oddity_holdings_png(base/"oddity-holdings.png"); daily=best_trader_of_day_png(base/"best-trader-of-day.png",snapshot)
        portfolios=await render_portfolio_cards(snapshot,base)
        result={"png":str(png),"html":str(html),"oddity_png":str(oddity),"best_trader_png":str(daily),"portfolio_pngs":portfolios}
        await bus.publish(MarketEvent("recap_ready",result)); return result
    async def maybe_auto_recap():
        nonlocal auto_recap_done
        if engine.soft_closed and not auto_recap_done:
            auto_recap_done=True
            await write_recap(Path("recaps/auto"))
    async def reconnect_card(status):
        status_card(Path("recaps/reconnecting.png"),status,"Twitch IRC dropped; automatic rejoin is in progress.")
        await bus.publish(__import__("kekw.events",fromlist=["MarketEvent"]).MarketEvent("reconnecting",{}))
    replay_delay=getattr(args,"delay",None)
    if replay_delay is None: replay_delay=.6 if args.source=="file" else 0
    if args.source=="irc" and not settings.twitch_bot_token:
        print("ANONYMOUS READ-ONLY: replies appear in the overlay only",flush=True)
    source=FileAdapter(args.path,delay=replay_delay) if args.source=="file" else IRCAdapter(args.channel,settings.twitch_bot_token,settings.twitch_client_id,settings.twitch_bot_username,on_status=reconnect_card)
    if args.web:
        import uvicorn
        from .web.server import create_app
        app=create_app(bus,prime=prime,oddity=oddity,red_key=settings.settle_key,desk=desk,engine=engine,recap_snapshot=recap_snapshot)
        first_client=app.state.first_client
        from contextlib import contextmanager
        class _NoSignalServer(uvicorn.Server):
            @contextmanager
            def capture_signals(self): yield None
        server=_NoSignalServer(uvicorn.Config(app,host=args.host,port=args.port,log_level="info"))
        server_task=asyncio.create_task(server.serve())
    desk_task=asyncio.create_task(desk.run(lambda:{"movers":engine.price_delta,"breaker_flags":list(engine.breaker_flags),"last_chat_lines":engine.chat[-40:],"recent_trades":engine.recent_trades},stop_event=stop))
    oddity_task=asyncio.create_task(oddity.run(stop))
    async def reply(msg,text):
        await publish_chat_reply(bus,source,msg.display_name,text)
    await bus.publish(MarketEvent("ingress",{"mode":engine.ingress_mode,"messages":0,"utc":datetime.now(timezone.utc).isoformat(),"last_chat_seconds":None}))
    if getattr(args,"showcase",False):
        for i in range(12):
            uid=f"pit_{i:02d}"
            await bus.publish(MarketEvent("pit_trade",{"user_id":uid,"display_name":f"PIT-{i:02d}","text":f"!buy $KEKW {8+i%9}","filled":True}))
    if args.web and args.source=="file":
        await asyncio.sleep(3)
        try:
            import webbrowser
            webbrowser.open(f"http://127.0.0.1:{args.port}/" + ("?stage=1" if getattr(args,"showcase",False) else ""))
        except Exception: pass
        if first_client:
            try: await asyncio.wait_for(first_client.wait(),timeout=10)
            except asyncio.TimeoutError: pass
    try:
        if getattr(args,"showcase",False):
            from .mock.showcase import Showcase
            timeline_path=Path(args.path).resolve()
            timeline=json.loads(timeline_path.read_text(encoding="utf-8"))
            showcase=Showcase(bus,engine,desk=desk,oddity=oddity,prime=prime,clock=market_clock)
            def advance_market_clock(seconds=5):
                if showcase_time is not None: showcase_time[0]+=seconds
            events=await showcase.run(timeline,timeline_path.parent,beat_delay=replay_delay,advance_market_clock=advance_market_clock)
            for event in events: print(f"SHOWCASE {event.kind}: {event.payload}",flush=True)
            await maybe_auto_recap()
            return
        async for msg in source:
            command=msg.text.strip()
            await engine.note_ingress(msg)
            await engine.touch_user(msg.user_id)
            if command.lower() in ("!balance","!portfolio","!top","!halp"):
                wallet=await store.wallet(msg.user_id)
                if command.lower()=="!balance": text=format_balance(msg.display_name,wallet['balance'])
                elif command.lower()=="!portfolio":
                    held=[(t,q) for (u,t),q in engine.positions.items() if u==msg.user_id and q>0]
                    text=f"@{msg.display_name} portfolio: "+(", ".join(f"${t} {q:.2f}" for t,q in held) if held else "empty")
                elif command.lower()=="!top":
                    top=(await store.wallets())[:5]; text="TOP 5: "+", ".join(f"{w['user_id']} {w['balance']:.1f}T" for w in top)
                else: text="Commands: !buy $T n, !sell $T n|all, !balance, !portfolio, !top, !found <emote>, !stake <title>, !recap"
                await reply(msg,text); continue
            found=re.fullmatch(r"!found\s+(\S+)",command,re.I)
            if found:
                ticker=sanitize_found_ticker(found.group(1))
                if not ticker: await reply(msg,"Oddity says that ticker looks like a keyboard sneeze."); continue
                prospectus=await desk.prospectus(ticker); await engine.list_ticker(ticker,prospectus); await reply(msg,f"${ticker} IPO at 50T — {prospectus}"); continue
            if command.lower().startswith("!stake "):
                if not msg.is_mod: await reply(msg,"Only a channel mod can open PRIME TIME."); continue
                contract=await prime.open(command[7:].strip(),60,is_mod=True)
                await reply(msg,f"PRIME TIME open: ${contract.yes_ticker} / ${contract.no_ticker} for 60s"); continue
            bet=re.fullmatch(r"!(yes|no)\s+(\d+)",command,re.I)
            if bet:
                contract=prime.active_contract
                if not contract: await reply(msg,"No PRIME TIME book is open."); continue
                side=bet.group(1).upper(); ticker=contract.yes_ticker if side=="YES" else contract.no_ticker
                try:
                    await prime.wager(contract.contract_id,msg.user_id,ticker,int(bet.group(2)),display_name=msg.display_name)
                    await reply(msg,f"@{msg.display_name} locked {bet.group(2)}T on ${ticker}")
                except ValueError as exc: await reply(msg,f"@{msg.display_name} {exc}")
                continue
            result=await engine.on_message(msg,count_ingress=False)
            await maybe_auto_recap()
            if command.lower().startswith(("!buy ","!sell ")):
                text=format_trade_reply(msg.display_name,command,result,engine.last_trade_error)
                await reply(msg,text)
            if msg.text.strip().lower()=="!recap":
                await write_recap(Path("recaps"))
                print("RECAP written to recaps/")
            if result is not None: print(f"ORDER {msg.display_name}: {msg.text} => {'FILLED' if result else 'REJECTED'}")
            for ticker in [x["ticker"] for x in await store.listings()]:
                for candle in engine.candles_for(ticker)[-1:]: print(f"CANDLE {candle.ticker} O={candle.open:.3f} H={candle.high:.3f} L={candle.low:.3f} C={candle.close:.3f}")
    except (asyncio.CancelledError, KeyboardInterrupt): pass
    finally:
        if isinstance(source,IRCAdapter):source.close()
        stop.set()
        if desk_task:
            try: await desk_task
            except asyncio.CancelledError: pass
        if oddity_task:
            try: await oddity_task
            except asyncio.CancelledError: pass
        if server:
            server.should_exit=True
            if server_task:
                await server_task
                await asyncio.sleep(0.1)
        await store.close()
        if showcase_temp: showcase_temp.cleanup()
def main():
    p=argparse.ArgumentParser(prog="python -m kekw");p.add_argument("--channel",required=True);p.add_argument("--source",choices=["file","irc"],default="irc");p.add_argument("--path",default=None);p.add_argument("--web",action="store_true");p.add_argument("--showcase",action="store_true",help="replay the staged JSON timeline into the web terminal");p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",default=8000,type=int);p.add_argument("--delay",type=float,default=None,help="seconds between file rows, showcase beats, and IPO messages (default: 3 for showcase, 0.6 for file, 0 for IRC)")
    args=p.parse_args()
    if args.showcase and not args.web: p.error("--showcase requires --web")
    if args.showcase and args.source!="file": p.error("--showcase requires --source file")
    if args.path is None:
        from pathlib import Path as _Path
        _root=_Path(__file__).resolve().parent.parent
        args.path=str(_root/ (
            "kekw/mock/demos/stage_timeline.json" if args.showcase else "kekw/mock/demos/stage_messages.jsonl"))
    if args.delay is None: args.delay=3.0 if args.showcase else .6 if args.source=="file" else 0
    if sys.platform=="win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try: asyncio.run(serve(args))
    except KeyboardInterrupt: pass
if __name__=="__main__":main()
