"""RED-KEY captures 15 fps PNG frames; deliberately never invokes a video encoder."""
import time
from pathlib import Path

def record_png_sequence(output_dir,duration_seconds=60,fps=15,monitor=1):
    try: import mss
    except ImportError as exc: raise RuntimeError("Install the optional mss dependency for RED-KEY capture") from exc
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); period=1/max(1,fps); end=time.monotonic()+duration_seconds; frame=0
    with mss.mss() as capture:
        display=capture.monitors[monitor]
        while time.monotonic()<end:
            started=time.monotonic(); capture.shot(mon=monitor,output=str(out/f"frame_{frame:06d}.png")); frame+=1
            time.sleep(max(0,period-(time.monotonic()-started)))
    return {"frames":frame,"fps":fps,"format":"png-sequence","directory":str(out)}
