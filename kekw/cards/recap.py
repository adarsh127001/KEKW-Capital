from pathlib import Path
from html import escape

W,H=1600,900
CYAN=(18,246,255); RED=(255,54,95); AMBER=(255,181,61); BG=(6,16,23); WHITE=(220,245,248)

def _canvas(title,mono=False):
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new("RGB",(W,H),BG); draw=ImageDraw.Draw(image)
    if mono:
        font=None
        for candidate in ("C:/Windows/Fonts/CascadiaMono.ttf","C:/Windows/Fonts/consola.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
            try: font=ImageFont.truetype(candidate,28); big=ImageFont.truetype(candidate,54); break
            except OSError: pass
        if font is None: font=ImageFont.load_default(); big=font
    else:
        try: font=ImageFont.truetype("arial.ttf",28); big=ImageFont.truetype("arialbd.ttf",54)
        except OSError: font=ImageFont.load_default(); big=font
    draw.text((48,32),title,font=big,fill=CYAN); return image,draw,font,big

def market_close_png(path,snapshot):
    image,draw,font,big=_canvas("MARKET CLOSE · KEKW CAPITAL")
    draw.text((50,120),"TODAY'S TAPE",font=big,fill=WHITE)
    chart=(50,205,1540,490); draw.rectangle(chart,outline=(25,80,90),width=2)
    series=snapshot.get("chart") or {}; closes=[float(v) for v in series.get("closes",[]) if v is not None]
    if closes:
        highs=[float(v) for v in series.get("highs",[])[:len(closes)]] or closes
        lows=[float(v) for v in series.get("lows",[])[:len(closes)]] or closes
        ticker=str(series.get("ticker") or "UNKNOWN").upper()
        lo=min(lows); hi=max(highs); span=hi-lo or max(abs(hi)*.04,1.0)
        lo-=span*.08; hi+=span*.08; span=hi-lo
        left,right,top,bottom=chart[0]+220,chart[2]-24,chart[1]+26,chart[3]-67
        for tick in range(5):
            value=hi-(hi-lo)*tick/4
            y=top+(bottom-top)*tick/4
            draw.line((left,y,right,y),fill=(25,80,90),width=1)
            label=f"${ticker} {value:.1f}T"
            box=draw.textbbox((0,0),label,font=font)
            draw.text((left-(box[2]-box[0])-12,y-(box[3]-box[1])/2),label,font=font,fill=CYAN)
        xs=([(left+right)/2] if len(closes)==1 else [left+i*(right-left)/(len(closes)-1) for i in range(len(closes))])
        ys=[bottom-(v-lo)/span*(bottom-top) for v in closes]
        color=CYAN if closes[-1]>=closes[0] else RED
        for i in range(0,len(closes),8):
            hy=bottom-(highs[min(i,len(highs)-1)]-lo)/span*(bottom-top)
            ly=bottom-(lows[min(i,len(lows)-1)]-lo)/span*(bottom-top)
            draw.line((xs[i],hy,xs[i],ly),fill=(130,205,210),width=2)
        if len(closes)>1: draw.line(list(zip(xs,ys)),fill=color,width=5)
        else: draw.line((xs[0]-8,ys[0],xs[0]+8,ys[0]),fill=color,width=5)
        buckets=series.get("buckets",[])
        indices=sorted(set((0,len(closes)//2,len(closes)-1)))
        for index in indices:
            elapsed=(int(buckets[index])-int(buckets[0]))*5 if index<len(buckets) and buckets else index*5
            label=f"{elapsed}s"; box=draw.textbbox((0,0),label,font=font); width=box[2]-box[0]
            x=max(left,min(right-width,xs[index]-width/2))
            draw.text((x,bottom+5),label,font=font,fill=CYAN)
        draw.text((chart[0]+16,chart[3]-34),f"${ticker} PRICE (T) · ELAPSED TIME (S)",font=font,fill=color)
    else:
        message="NO MARKET DATA — RELEASE THE CHAT"
        box=draw.textbbox((0,0),message,font=font); text_w=box[2]-box[0]; text_h=box[3]-box[1]
        draw.text(((chart[0]+chart[2]-text_w)/2,(chart[1]+chart[3]-text_h)/2),message,font=font,fill=CYAN)
    headlines=snapshot.get("headlines",[])[:3]; draw.text((50,525),"TOP HEADLINES",font=big,fill=CYAN)
    for i,line in enumerate(headlines): draw.text((60,590+i*42),f"{i+1}. {line[:110]}",font=font,fill=WHITE)
    verdict=" · ".join(snapshot.get("verdicts",[])[:3]) or "No PRIME TIME verdicts this stream."
    draw.text((50,735),f"VERDICTS  {verdict[:105]}",font=font,fill=WHITE)
    leaders=snapshot.get("top_pnl",[])[:3]; text="   ".join(f"{x.get('display_name','trader')} {x.get('pnl',0):+.1f}T" for x in leaders) or "No settled P&L yet"
    draw.text((50,800),f"TOP P&L  {text[:105]}",font=font,fill=CYAN); Path(path).parent.mkdir(parents=True,exist_ok=True); image.save(path); return Path(path)

def portfolio_png(path,display_name,holdings,pnl,roast):
    image,draw,font,big=_canvas(f"{display_name.upper()} · TENDIES PORTFOLIO")
    draw.text((55,140),f"TOTAL P&L  {pnl:+.1f}T",font=big,fill=CYAN if pnl>=0 else RED)
    y=245
    for ticker,qty,value in holdings[:12]: draw.text((65,y),f"${ticker:<18} {qty:>8.2f} shares   {value:>8.2f}T",font=font,fill=WHITE); y+=45
    draw.text((55,800),f"ODDITY SAYS: {roast[:95]}",font=font,fill=CYAN); Path(path).parent.mkdir(parents=True,exist_ok=True); image.save(path); return Path(path)

def oddity_holdings_png(path):
    image,draw,font,big=_canvas("ODDITY HOLDINGS · INTERNAL MEMO")
    draw.text((80,250),"-87%",font=big,fill=RED); draw.text((80,370),"I CALLED THE LINE.",font=big,fill=CYAN)
    draw.text((80,470),"(The line called back. It was a margin call.)",font=font,fill=WHITE)
    Path(path).parent.mkdir(parents=True,exist_ok=True); image.save(path); return Path(path)

def best_trader_of_day_png(path,snapshot):
    image,draw,font,big=_canvas("SEASON BOARD · DAILY TENDIES LEADER",mono=True)
    leader=snapshot.get("best_trader") or {}
    draw.text((60,145),"BEST TRADER OF THE DAY",font=big,fill=CYAN)
    if leader:
        name=str(leader.get("display_name") or leader.get("user_id") or "UNKNOWN")
        pnl=float(leader.get("pnl",0))
        draw.text((65,245),name.upper()[:35],font=big,fill=CYAN)
        draw.text((65,330),f"NET TENDIES FLOW TODAY  {pnl:+.1f}T",font=big,fill=CYAN if pnl>=0 else RED)
        draw.text((65,405),f"UTC SESSION  {leader.get('utc_date','TODAY')}",font=font,fill=CYAN)
    else:
        draw.text((65,270),"NO TRADING LEDGER ENTRIES TODAY",font=big,fill=CYAN)
    draw.text((60,520),"VERDICT-CALL STREAK BADGES",font=big,fill=AMBER)
    streaks=snapshot.get("verdict_streaks",[])[:5]
    if streaks:
        for index,row in enumerate(streaks):
            name=str(row.get("display_name") or row.get("user_id") or "TRADER")
            current=int(row.get("current_streak",0)); best=int(row.get("best_streak",0))
            draw.text((75,600+index*48),f"#{index+1} {name[:24].upper()}  CURRENT {current}  SEASON BEST {best}",font=font,fill=CYAN)
    else:
        draw.text((75,610),"NO CORRECT VERDICT CALLS RECORDED YET",font=font,fill=CYAN)
    Path(path).parent.mkdir(parents=True,exist_ok=True); image.save(path); return Path(path)

def status_card(path,title,message):
    image,draw,font,big=_canvas(title.upper()); draw.text((60,260),message[:120],font=big,fill=RED); draw.text((60,360),"Fallback active · local market data preserved",font=font,fill=WHITE)
    Path(path).parent.mkdir(parents=True,exist_ok=True); image.save(path); return Path(path)

def html_recap(path,snapshot):
    items="".join(f"<li>{escape(str(x))}</li>" for x in snapshot.get("headlines",[])[:3])
    rows="".join(f"<tr><td>{escape(str(x.get('display_name','trader')))}</td><td>{float(x.get('pnl',0)):+.1f}T</td></tr>" for x in snapshot.get("top_pnl",[])[:10])
    html=f"<!doctype html><meta charset='utf-8'><title>MARKET CLOSE</title><style>body{{background:#061017;color:#dcf5f8;font:22px Arial;margin:5vw}}h1{{color:#12f6ff}}a{{color:#12f6ff}}</style><h1>MARKET CLOSE · KEKW CAPITAL</h1><h2>Headlines</h2><ol>{items}</ol><h2>Top P&amp;L</h2><table>{rows}</table>"
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(html,encoding="utf-8"); return Path(path)
