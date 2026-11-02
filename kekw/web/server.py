from collections import deque
from dataclasses import asdict, is_dataclass
from pathlib import Path
import asyncio, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ..desk.oddity import Oddity
from ..events import Headline, MarketEvent
from ..market.contracts import PrimeTime
from ..market.engine import Candle

STATIC=Path(__file__).parent/"static"
AUDIO=STATIC.parents[2]/"assets"/"audio"
def serial(event):
    if is_dataclass(event): return {"type":type(event).__name__,**asdict(event)}
    return {"type":type(event).__name__,"payload":event}

def create_app(bus,*,prime=None,oddity=None,mode="SHOWCASE",red_key=None,desk=None,engine=None,recap_snapshot=None):
    app=FastAPI(title="KEKW CAPITAL Terminal"); clients=set(); history=deque(maxlen=800); forward_lock=asyncio.Lock(); first_client=asyncio.Event(); app.state.mode=mode; app.state.first_client=first_client
    app.mount("/static",StaticFiles(directory=STATIC),name="static")
    app.state.prime=prime or PrimeTime(bus=bus); app.state.oddity=oddity or Oddity(bus=bus); app.state.red_key=red_key
    app.state.desk=desk; app.state.engine=engine; app.state.recap_snapshot=recap_snapshot
    from ..pit.traders import PitTraders
    app.state.pit_traders=PitTraders(bus,engine) if engine else None
    app.state.pit_tick_task=None
    async def run_pit_ticker():
        while app.state.mode=="PIT":
            await app.state.engine.batch(force=True)
            await asyncio.sleep(1)
    def start_pit_ticker():
        if engine and (app.state.pit_tick_task is None or app.state.pit_tick_task.done()):
            app.state.pit_tick_task=asyncio.create_task(run_pit_ticker())
    @app.on_event("startup")
    async def startup():
        app.state.forwarder=asyncio.create_task(forward())
        if app.state.mode=="PIT": start_pit_ticker()
    @app.on_event("shutdown")
    async def shutdown():
        task=getattr(app.state,"forwarder",None)
        if task: task.cancel()
        task=app.state.pit_tick_task
        if task: task.cancel()
    async def forward():
        queues=[bus.subscribe(MarketEvent),bus.subscribe(Headline),bus.subscribe(Candle)]
        while True:
            tasks=[asyncio.create_task(q.get()) for q in queues]
            done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
            for task in pending: task.cancel()
            for task in done:
                event=task.result()
                if app.state.mode=="PIT" and app.state.pit_traders:
                    await app.state.pit_traders.on_event(event)
                event_data=serial(event)
                async with forward_lock:
                    history.append(event_data)
                    data=json.dumps(event_data,default=str)
                    for ws in tuple(clients):
                        try: await ws.send_text(data)
                        except Exception: clients.discard(ws)
    NO_STORE={"Cache-Control":"no-store, no-cache, must-revalidate"}
    @app.get("/")
    async def terminal(): return FileResponse(STATIC/"terminal.html",headers=NO_STORE)
    @app.get("/dash")
    async def dash(): return FileResponse(STATIC/"dash.html",headers=NO_STORE)
    @app.get("/favicon.ico",include_in_schema=False)
    async def favicon(): return FileResponse(STATIC/"favicon.svg",media_type="image/svg+xml")
    @app.get("/audio-manifest",include_in_schema=False)
    async def audio_manifest(): return {"files":sorted(path.name for path in AUDIO.glob("*.wav") if path.is_file())}
    @app.api_route("/audio/{name}", methods=["GET", "HEAD"])
    async def audio(name:str):
        if "/" in name or "\\" in name or not name.endswith(".wav"): return {"ok":False}
        path=AUDIO/name
        if not path.is_file(): raise HTTPException(status_code=404,detail="audio not found")
        return FileResponse(path,media_type="audio/wav")
    @app.websocket("/ws")
    async def websocket(ws:WebSocket):
        await ws.accept()
        async with forward_lock:
            await ws.send_text(json.dumps({"type":"history","events":list(history)},default=str))
            await ws.send_text(json.dumps(serial(MarketEvent("mode",{"mode":app.state.mode})),default=str))
            clients.add(ws)
            first_client.set()
        try:
            await ws.send_text(json.dumps(serial(MarketEvent("mode",{"mode":app.state.mode})),default=str))
            while True: await ws.receive_text()
        except WebSocketDisconnect: clients.discard(ws)
    @app.post("/control/mode/{value}")
    async def set_mode(value:str):
        if value not in ("LIVE","PIT","SHOWCASE"): return {"ok":False,"error":"invalid mode"}
        app.state.mode=value
        if value=="PIT": start_pit_ticker()
        elif app.state.pit_tick_task and not app.state.pit_tick_task.done(): app.state.pit_tick_task.cancel()
        await bus.publish(MarketEvent("mode",{"mode":value})); return {"ok":True,"mode":value}
    @app.post("/control/stake")
    async def open_stake(payload:dict):
        c=await app.state.prime.open(payload.get("title","Untitled stake"),int(payload.get("window",60)),is_mod=True)
        return {"id":c.contract_id,"yes":c.yes_ticker,"no":c.no_ticker,"anchor":50}
    @app.post("/control/probe")
    async def probe(payload:dict):
        import re
        ticker=payload.get("emote","").upper()
        if not re.fullmatch(r"[A-Z0-9_]{2,}",ticker):
            await bus.publish(MarketEvent("chat_reply",{"text":"Oddity says that ticker looks like a keyboard sneeze."}))
            return {"ok":False,"error":"Oddity cannot list that ticker."}
        prospectus=await app.state.desk.prospectus(ticker) if getattr(app.state,"desk",None) else "Community discovered ticker."
        created=await app.state.engine.list_ticker(ticker,prospectus) if getattr(app.state,"engine",None) else False
        return {"ok":True,"ticker":ticker,"prospectus":prospectus,"created":created}
    @app.post("/control/found")
    async def force_found(payload:dict):
        return await probe(payload)
    @app.patch("/control/settle")
    async def settle(payload:dict):
        if app.state.red_key and payload.get("key")!=app.state.red_key: return {"ok":False,"error":"invalid settle key"}
        if not payload.get("key"): return {"ok":False,"error":"settle key required"}
        result=await app.state.prime.settle(payload["contract_id"],payload["winner"],settle_key=True); return {"ok":True,**result}
    @app.post("/control/red-key")
    async def red_key():
        await app.state.oddity.on_event("RED_KEY"); await bus.publish(MarketEvent("red_key",{}))
        from ..cards.red_key import record_png_sequence
        app.state.capture_task=asyncio.create_task(asyncio.to_thread(record_png_sequence,"recordings/red-key",120,15))
        return {"ok":True,"mode":"RED-KEY","recording":"recordings/red-key/"}
    @app.post("/control/force-crash")
    async def force_crash():
        await app.state.oddity.on_event("FORCE_CRASH"); await bus.publish(MarketEvent("force_crash",{})); return {"ok":True,"state":"SCREAMING"}
    @app.post("/control/snake-death")
    async def snake_death():
        await bus.publish(MarketEvent("snake_death",{"verdict":"Oddity LOSES"}))
        await bus.publish(MarketEvent("verdict",{"winner":"ODDY_LOSE","source":"snake"}))
        await app.state.oddity.on_event(MarketEvent("verdict",{"winner":"ODDY_LOSE"}))
        return {"ok":True,"winner":"ODDY_LOSE"}
    @app.post("/control/recap")
    async def recap(payload:dict):
        from ..cards.recap import best_trader_of_day_png, html_recap, market_close_png, oddity_holdings_png, portfolio_png
        import re
        base=Path(payload.get("directory","recaps")); snapshot=await app.state.recap_snapshot() if getattr(app.state,"recap_snapshot",None) else payload.get("snapshot",{})
        png=market_close_png(base/"market-close.png",snapshot); html=html_recap(base/"index.html",snapshot); oddity=oddity_holdings_png(base/"oddity-holdings.png"); daily=best_trader_of_day_png(base/"best-trader-of-day.png",snapshot)
        engine=getattr(app.state,"engine",None); listings={row["ticker"]:row for row in await engine.store.listings()} if engine else {}; portfolios=[]; used=set()
        for row in snapshot.get("top_pnl",[])[:5]:
            user_id=str(row.get("user_id") or row.get("display_name") or "trader"); name=str(row.get("display_name") or user_id)
            slug=re.sub(r"[^A-Za-z0-9_-]+","_",name).strip("_") or "trader"
            if slug in used: slug=f"{slug}_{re.sub(r'[^A-Za-z0-9_-]+','_',user_id)}"
            used.add(slug)
            holdings=[(ticker,shares,shares*float(listings.get(ticker,{}).get("price",0))) for (owner,ticker),shares in (engine.positions.items() if engine else []) if owner==user_id and shares>0]
            roast=["Bold entry. The exit remains a mystery.","Someone call the line back.","Sell the rumor, lose the news.","The tape remembers.","Certified bagholder of the day."][hash(user_id)%5]
            portfolios.append(str(portfolio_png(base/"portfolios"/f"{slug}.png",name,holdings,float(row.get("pnl",0)),roast)))
        result={"png":str(png),"html":str(html),"oddity_png":str(oddity),"best_trader_png":str(daily),"portfolio_pngs":portfolios}
        await bus.publish(MarketEvent("recap_ready",result)); return result
    @app.post("/control/tape")
    async def tape(payload:dict|None=None):
        from ..cards.recap import best_trader_of_day_png, html_recap, market_close_png, oddity_holdings_png
        from ..cards.tape import render_tape_video
        payload=payload or {}; base=Path(payload.get("directory","recaps"))
        snapshot=await app.state.recap_snapshot() if getattr(app.state,"recap_snapshot",None) else payload.get("snapshot",{})
        close=market_close_png(base/"market-close.png",snapshot)
        html=html_recap(base/"index.html",snapshot)
        oddity=oddity_holdings_png(base/"oddity-holdings.png")
        daily=best_trader_of_day_png(base/"best-trader-of-day.png",snapshot)
        cards=[str(close),str(daily),str(oddity)]
        try:
            desk=app.state.desk
            video=await render_tape_video(base/"tape.mp4",cards,snapshot,
                api_key=getattr(desk,"api_key",None),client=getattr(desk,"client",None))
        except Exception as exc:
            return {"ok":False,"error":str(exc),"video":None,"fallback":{"png":str(close),"html":str(html),"cards":cards}}
        return {"ok":True,"video":str(video),"png":str(close),"html":str(html),"cards":cards}
    return app
