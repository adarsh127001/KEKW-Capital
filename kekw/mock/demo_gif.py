"""Render a 60-frame, network-free README animation from the checked-in showcase."""
import json
import math
import tempfile
from types import SimpleNamespace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .. import store as store_module
from ..bus import EventBus
from ..config import Settings
from ..market.engine import MarketEngine
from ..store import Store
from .showcase import Showcase

ROOT=Path(__file__).resolve().parents[2]
TIMELINE=ROOT/"kekw"/"mock"/"demos"/"stage_timeline.json"
OUT=ROOT/"docs"/"assets"/"showcase.gif"
SIZE=(1280,720)
INK="#061017"; CYAN="#12f6ff"; CRIMSON="#ff365f"; AMBER="#FFB53D"


def _font(size):
    candidates=[
        Path("C:/Windows/Fonts/CascadiaMono.ttf"),Path("C:/Windows/Fonts/consola.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/Library/Fonts/Courier New.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try: return ImageFont.truetype(str(path),size)
            except OSError: pass
    return ImageFont.load_default()


def _panel(draw,box,color=CYAN):
    x1,y1,x2,y2=box; draw.rectangle(box,outline=color,width=2)
    length=22
    for x,y,dx,dy in ((x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)):
        draw.line((x,y,x+dx*length,y),fill=color,width=4)
        draw.line((x,y,x,y+dy*length),fill=color,width=4)


def _run_immediate(awaitable):
    """Drive the showcase's no-I/O coroutines when its SQLite adapter is synchronous."""
    while True:
        try: yielded=awaitable.send(None)
        except StopIteration as finished: return finished.value
        if yielded is not None:
            raise RuntimeError("showcase requested async I/O; use the fixture renderer")


def _showcase_data():
    timeline=json.loads(TIMELINE.read_text(encoding="utf-8"))
    if not hasattr(store_module.aiosqlite,"Connection"):
        with tempfile.TemporaryDirectory(prefix="kekw-gif-") as temp:
            store=Store(str(Path(temp)/"showcase.db"))
            try:
                _run_immediate(store.open())
                bus=EventBus(); engine=MarketEngine(store,bus=bus,settings=Settings())
                _run_immediate(engine.initialize())
                showcase=Showcase(bus,engine)
                events=_run_immediate(showcase.run(timeline,TIMELINE.parent))
                listings=_run_immediate(store.listings())
                history={ticker:[price for _,price in values] for ticker,values in engine.history.items()}
                for row in listings:
                    series=history.get(row["ticker"],[])
                    history[row["ticker"]]=[float(row["price"]),*(series or [float(row["price"])])]
                return timeline,events,listings,history
            finally:
                _run_immediate(store.close())
    return _fixture_showcase_data(timeline)


def _fixture_showcase_data(timeline=None):
    """Read the checked-in showcase timeline and chat fixture; never use network or DB."""
    timeline=timeline or json.loads(TIMELINE.read_text(encoding="utf-8"))
    message_path=TIMELINE.parent/timeline["message_file_relative"]
    messages=[json.loads(line) for line in message_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    events=[]; tickers={"KEKW","GG","FAIL"}; listings=[{"ticker":ticker,"price":50.0} for ticker in ("KEKW","GG","FAIL")]
    def emit(kind,payload): events.append(SimpleNamespace(kind=kind,payload=payload))
    for beat in timeline["beats"]:
        emit("stage_beat",{"id":beat["id"],"label":beat["label"]})
        if beat["kind"]=="ipo_flood":
            for index in beat.get("messages",range(len(messages))):
                message=messages[index]
                tokens=[str(token).upper().lstrip("$") for token in message.get("tokens",[])]
                for ticker in dict.fromkeys(tokens):
                    if ticker not in tickers and tokens.count(ticker)>=3:
                        tickers.add(ticker); listings.append({"ticker":ticker,"price":50.0})
                        emit("ipo",{"ticker":ticker,"anchor":50,"prospectus":"Community discovered ticker."})
        elif beat["kind"]=="named_kill":
            message=messages[beat["message"]]; user_id=message.get("user_id","")
            booth=user_id.upper().replace("_","-") if user_id.lower().startswith("booth_") else None
            emit("stage_breaking",{"user":message.get("display_name",user_id),"ticker":"KEKW","text":message.get("text",""),"booth":booth})
        elif beat["kind"]=="headline_prompt": emit("headline_prompt",{"emote":beat["emote"]})
        elif beat["kind"]=="stake_open":
            safe="".join(ch for ch in beat["title"].upper() if ch.isalnum())[:12] or "DUEL"
            emit("stake_open",{"id":"PT001","title":beat["title"],"yes":f"{safe}_YES","no":f"{safe}_NO","anchor":50})
            emit("contract_order",{"yes_tendies":10,"no_tendies":5})
        elif beat["kind"]=="verdict":
            emit("contract_settled",{"winner":beat["winner"],"burned":0.5})
            emit("verdict",{"winner":beat["winner"]})
        else: emit(beat["kind"],beat.get("payload",{}))
    history={row["ticker"]:[row["price"],row["price"]] for row in listings}
    # The first IPO flood message is three POGCHAMP tokens in one 5s bucket;
    # this is the engine's locked EMA impulse at the 50T anchor.
    if "POGCHAMP" in tickers:
        momentum=((.3*3)+.01)/((.01*3)+.01)
        history["POGCHAMP"]=[50.0,50.0*(1+min(.25,max(-.25,.05*math.log(momentum))))]
    return timeline,events,listings,history


def _event_payloads(events,kind):
    return [event.payload for event in events if event.kind==kind]


def _beat_copy(beat,events):
    beat_id=beat["id"]
    if beat_id=="open": return "MARKET. IS. OPEN. I AM THE MARKET."
    if beat_id=="ipo_flood":
        tickers=[str(item.get("ticker","")) for item in _event_payloads(events,"ipo")]
        return "IPO FLOOD  ·  "+"   ".join(f"${ticker} @ 50T" for ticker in tickers[:5])
    if beat_id=="named_kill":
        item=next(iter(_event_payloads(events,"stage_breaking")),{})
        return f"BREAKING: {item.get('booth') or item.get('user','BOOTH TRADER')} PUTS $KEKW ON THE TAPE"
    if beat_id=="probe": return f"AI DESK PROBE  ·  {beat.get('emote','EMOTE')} — TEMPLATE ALWAYS READY"
    if beat_id=="stake_open":
        item=next(iter(_event_payloads(events,"stake_open")),{})
        return f"PRIME TIME  ·  ${item.get('yes','YES')} / ${item.get('no','NO')}"
    if beat_id=="verdict":
        item=next(iter(_event_payloads(events,"contract_settled")),{})
        return f"VERDICT: ${item.get('winner',beat.get('winner','ODDY_LOSE'))} WINS  ·  1.9X"
    return "MARKET CLOSE  ·  ODDITY HOLDINGS: -87%"


def _draw_frame(frame_index,timeline,events,listings,history):
    image=Image.new("RGB",SIZE,INK); draw=ImageDraw.Draw(image)
    small=_font(17); medium=_font(25); large=_font(42); price_font=_font(30)
    beat_count=len(timeline["beats"])
    beat_index=min(beat_count-1,frame_index*beat_count//60)
    local=frame_index-(beat_index*60//beat_count)
    beat=timeline["beats"][beat_index]; copy=_beat_copy(beat,events)
    reveal=max(1,round(len(copy)*min(1,(local+1)/max(1,60/beat_count))))
    jitter=2 if local==0 and beat_index in (2,5,6) else 0
    dx=(frame_index%2)*jitter

    draw.text((58,35),"KEKW CAPITAL  //  POST-STREAM TAPE",font=large,fill=CYAN)
    draw.text((62,94),"INGRESS: SHOWCASE   //   OFFLINE DEMO   //   60 FRAMES",font=small,fill=AMBER)
    draw.line((62,117,1218,117),fill=CRIMSON,width=2)
    draw.line((62,117,62+int(1156*(frame_index+1)/60),117),fill=CYAN,width=4)
    draw.text((62+dx,137),copy[:reveal],font=medium,fill=CRIMSON if beat_index in (2,5) else CYAN)

    _panel(draw,(54,190,842,592),CYAN)
    draw.text((78,210),"5 SECOND MARKET CANDLES",font=medium,fill=CYAN)
    chart=(96,270,805,548); draw.line((96,548,805,548),fill=CYAN,width=2)
    market_listings=[row for row in listings if not row["ticker"].endswith(("_YES","_NO"))]
    symbols=[row["ticker"] for row in market_listings if row["ticker"] in ("KEKW","GG","FAIL","POGCHAMP")][:4]
    if not symbols: symbols=[row["ticker"] for row in market_listings[:4]]
    for row_index,ticker in enumerate(symbols):
        series=history.get(ticker,[])
        if not series:
            series=[float(next((row["price"] for row in listings if row["ticker"]==ticker),50.0))]
        color=CYAN if row_index%2==0 else CRIMSON
        level=326+row_index*57
        shown=max(1,min(len(series),int((local+1)/max(1,60/beat_count)*len(series))))
        visible=series[:shown]
        draw.text((105,level-30),f"${ticker}",font=small,fill=color)
        points=[]
        for i,value in enumerate(visible):
            x=250+i*min(86,480/max(1,len(visible)))
            y=level-max(-18,min(18,(value-50)*24))
            points.append((x,y))
        if len(points)>1: draw.line(points,fill=color,width=4)
        for x,y in points: draw.rectangle((x-3,y-3,x+3,y+3),fill=color)
        last=visible[-1]
        draw.text((650,level-22),f"{last:.2f}T ${ticker}",font=small,fill=color)

    _panel(draw,(876,190,1226,592),AMBER)
    draw.text((900,210),"MARKET TAPE",font=medium,fill=AMBER)
    y=278
    for row in market_listings[:4]:
        series=history.get(row["ticker"],[])
        value=series[-1] if series else float(row["price"])
        draw.text((900,y),f"${row['ticker']}",font=small,fill=CYAN)
        draw.text((900,y+26),f"{value:.2f}T",font=price_font,fill=CYAN)
        y+=70

    _panel(draw,(54,622,1226,687),CYAN)
    tickerline="   //   ".join(f"${row['ticker']} {history.get(row['ticker'],[row['price']])[-1]:.1f}T" for row in market_listings[:4])
    draw.text((75,642),f"{tickerline}   //   {tickerline}",font=_font(14),fill=CYAN)
    return image


def generate(output=OUT):
    source="offline Showcase runner" if not hasattr(store_module.aiosqlite,"Connection") else "SHOWCASE timeline and chat fixture"
    print(f"Rendering from {source}...",flush=True)
    timeline,events,listings,history=_showcase_data()
    print(f"Drawing 60 frames from {len(events)} showcase events...",flush=True)
    frames=[_draw_frame(i,timeline,events,listings,history) for i in range(60)]
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    palette=Image.new("P",(1,1)); palette.putpalette([6,16,23,18,246,255,255,54,95,255,181,61]+[0]*756)
    print("Encoding GIF...",flush=True)
    palette_frames=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    palette_frames[0].save(output,save_all=True,append_images=palette_frames[1:],duration=100,loop=0,optimize=True,disposal=2)
    return output


if __name__=="__main__":
    result=generate()
    print(f"Wrote {result} (60 showcase frames)")
