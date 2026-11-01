"""Generate local synth WAV effects and optionally batch-render Oddity TTS."""
import asyncio, math, os, struct, wave
from pathlib import Path

SFX={"tape_tick":(880,.07),"riser":(440,.7),"klaxon":(280,.6),"siren":(520,.8),"confetti_pop":(1200,.25),"market_close":(330,.5)}
VOICE={"OPEN":"The KEKW Capital market is open. I called the line.","CALLED_IT":"I called the line. This time I meant the other line.","HUBRIS":"There is no such thing as overconfidence when I am correct.","PANIC":"That is not a drawdown. That is a character building exercise.","SULK":"I remain bullish on the concept of being right eventually.","MARKET_CLOSED":"The market is closed. My positions are a private matter.","IDLE_1":"Quiet tape. The market is just saving its best move for my prediction.","IDLE_2":"I have reviewed the charts. They are clearly impressed with me.","IDLE_3":"Silence from the pit. A wise audience knows when the host is right.","IDLE_4":"The candles are calm. I remain aggressively confident.","IDLE_5":"No trades, no panic. Finally, a market with proper respect."}
def synth(path,freq,duration,sample_rate=22050):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate); frames=[]
        for n in range(int(duration*sample_rate)):
            t=n/sample_rate; env=min(1,n/(sample_rate*.01),max(0,(duration*sample_rate-n)/(sample_rate*.03)))
            f=freq+(freq*.8*t/duration if path.stem=="riser" else 0); frames.append(struct.pack("<h",int(10000*env*math.sin(2*math.pi*f*t))))
        w.writeframes(b"".join(frames))
def normalize_wav_header(path):
    path=Path(path); size=path.stat().st_size
    with path.open("r+b") as audio:
        header=audio.read(12)
        if header[:4]!=b"RIFF" or header[8:12]!=b"WAVE": raise ValueError(f"Not a RIFF/WAVE file: {path}")
        audio.seek(4); audio.write(struct.pack("<I",size-8))
        offset=12
        while offset+8<=size:
            audio.seek(offset); chunk=audio.read(8)
            chunk_id,chunk_size=chunk[:4],struct.unpack("<I",chunk[4:])[0]
            if chunk_id==b"data":
                audio.seek(offset+4); audio.write(struct.pack("<I",size-offset-8)); return
            offset+=8+chunk_size+(chunk_size&1)
        raise ValueError(f"WAVE data chunk missing: {path}")
async def generate(output="assets/audio",voices=False):
    path=Path(output); path.mkdir(parents=True,exist_ok=True)
    for name,(freq,dur) in SFX.items(): synth(path/f"{name}.wav",freq,dur)
    if voices:
        from openai import AsyncOpenAI
        api_key=os.getenv("OPENAI_API_KEY")
        if not api_key:
            from ..config import Settings
            api_key=Settings.from_env().openai_api_key
        if not api_key: raise RuntimeError("OPENAI_API_KEY is required to generate Oddity voice WAVs")
        client=AsyncOpenAI(api_key=api_key,max_retries=1,timeout=30)
        for name,text in VOICE.items():
            target=path/f"{name.lower()}.wav"
            print(f"VOICE {target.stem} → generating",flush=True)
            response=await client.audio.speech.create(model="tts-1",voice="onyx",input=text,response_format="wav")
            response.write_to_file(target)
            normalize_wav_header(target)
            print(f"VOICE {target.stem} → ok ({target.stat().st_size} bytes)",flush=True)
            print(f"  path: {target}",flush=True)
if __name__=="__main__": asyncio.run(generate(voices=os.getenv("KEKW_GENERATE_VOICES")=="1"))
