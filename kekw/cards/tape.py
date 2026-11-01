"""Build an optional post-stream MP4 from recap cards and an offline desk read."""
import asyncio
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


def desk_read(snapshot):
    headlines=snapshot.get("headlines",[])[:2]
    verdicts=snapshot.get("verdicts",[])[:2]
    leader=snapshot.get("best_trader") or {}
    streaks=snapshot.get("verdict_streaks",[])
    streak=streaks[0] if streaks else {}
    headline_text=" ".join(str(line) for line in headlines) or "The tape closed without a headline."
    verdict_text=" ".join(str(line) for line in verdicts) or "No PRIME TIME verdict was recorded."
    leader_text=(f"Today's best Tendies flow belongs to {leader.get('display_name') or leader.get('user_id')}, "
                 f"at {float(leader.get('pnl',0)):+.1f} Tendies.") if leader else "No daily trader is recorded yet."
    streak_text=(f"The season verdict-call streak leader is {streak.get('display_name') or streak.get('user_id')}, "
                 f"with {int(streak.get('current_streak',0))} current and {int(streak.get('best_streak',0))} best correct calls.") if streak else "The season badge is still up for grabs."
    return [
        f"Market close. {headline_text} {verdict_text}",
        f"Season board. {leader_text} {streak_text}",
        "Oddity Holdings is down eighty-seven percent. Oddity says it called that line; the margin call disagrees.",
    ]


def _wav_seconds(path):
    with wave.open(str(path),"rb") as audio:
        # tts-1 WAVs may advertise 0xFFFFFFFF data bytes in RIFF; bound the
        # header frame count by the PCM bytes actually present in the file.
        payload_start=audio._data_chunk.offset+8
        frame_size=audio.getnchannels()*audio.getsampwidth()
        available_frames=max(0,(Path(path).stat().st_size-payload_start)//frame_size)
        return min(audio.getnframes(),available_frames)/float(audio.getframerate())


async def render_tape_video(output,images,snapshot,*,api_key=None,client=None,ffmpeg=None):
    """Render card stills and their matching tts-1 narration segments into one MP4."""
    key=api_key or os.getenv("OPENAI_API_KEY")
    if client is None and not key:
        raise RuntimeError("OPENAI_API_KEY is required for the post-stream desk read")
    binary=ffmpeg or os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg")
    if not binary or (Path(binary).is_absolute() and not Path(binary).is_file()):
        raise RuntimeError("ffmpeg was not found; PNG and HTML recap fallbacks are ready")
    card_paths=[Path(image) for image in images]
    if not card_paths or any(not path.is_file() for path in card_paths):
        raise RuntimeError("all recap card PNGs must exist before rendering the tape")
    if client is None:
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=key)

    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    reads=desk_read(snapshot)
    if len(reads)!=len(card_paths):
        raise ValueError("each recap card needs one desk-read segment")
    with tempfile.TemporaryDirectory(prefix="kekw-tape-",dir=output.parent) as folder:
        temp=Path(folder); audio_paths=[]; durations=[]
        for index,text in enumerate(reads):
            wav_path=temp/f"read-{index:02d}.wav"
            response=await client.audio.speech.create(model="tts-1",voice="onyx",input=text,response_format="wav")
            response.write_to_file(wav_path)
            duration=_wav_seconds(wav_path)
            if duration<=0: raise RuntimeError("tts-1 returned an empty desk-read segment")
            audio_paths.append(wav_path); durations.append(duration)

        args=[str(binary),"-y"]
        for image,audio,duration in zip(card_paths,audio_paths,durations):
            args.extend(["-loop","1","-framerate","30","-t",f"{duration:.3f}","-i",str(image),"-i",str(audio)])
        filters=[]; concat=[]
        for index,duration in enumerate(durations):
            video_index=index*2; audio_index=video_index+1
            filters.append(f"[{video_index}:v]fps=30,scale=1600:900,setsar=1,trim=duration={duration:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{index}]")
            filters.append(f"[{audio_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duration:.3f},asetpts=PTS-STARTPTS[a{index}]")
            concat.extend([f"[v{index}]",f"[a{index}]"])
        filters.append("".join(concat)+f"concat=n={len(card_paths)}:v=1:a=1[vout][aout]")
        partial=output.with_name(output.stem+".partial"+output.suffix)
        args.extend(["-filter_complex",";".join(filters),"-map","[vout]","-map","[aout]","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",str(partial)])
        try:
            result=await asyncio.to_thread(subprocess.run,args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("ffmpeg tape render timed out") from exc
        if result.returncode!=0:
            detail=result.stderr.decode("utf-8",errors="replace")[-1600:]
            raise RuntimeError(f"ffmpeg tape render failed: {detail or result.stdout.decode('utf-8',errors='replace')[-500:]}")
        if not partial.is_file() or partial.stat().st_size==0:
            raise RuntimeError("ffmpeg did not produce a tape file")
        partial.replace(output)
    return output
