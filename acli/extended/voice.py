"""Cross-platform text-to-speech and microphone capture MVP."""
import platform, shutil, subprocess
from pathlib import Path

def speak(text: str) -> str:
    system=platform.system()
    if system=='Windows':
        safe=text.replace("'","''")
        cmd=['powershell','-NoProfile','-Command',"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('"+safe+"')"]
    elif system=='Darwin' and shutil.which('say'): cmd=['say',text]
    elif shutil.which('espeak'): cmd=['espeak',text]
    else: return 'No system text-to-speech command found.'
    subprocess.Popen(cmd); return 'Speaking '+str(len(text))+' characters.'

def transcribe_audio(workspace: str, rel_path: str, api_key: str, base_url: str = 'https://api.openai.com/v1', model: str = 'whisper-1') -> str:
    root=Path(workspace).resolve(); path=(root/rel_path).resolve()
    if root not in path.parents or not path.exists(): raise PermissionError('Audio path is outside the workspace or missing')
    from openai import OpenAI
    with path.open('rb') as audio:
        result=OpenAI(api_key=api_key,base_url=base_url).audio.transcriptions.create(model=model,file=audio)
    return getattr(result,'text',str(result))

def record_audio(workspace: str, seconds: int = 5, filename: str = 'voice.wav') -> str:
    if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg is required')
    out=Path(workspace)/Path(filename).name; system=platform.system()
    if system=='Windows': cmd=['ffmpeg','-y','-f','dshow','-i','audio=default','-t',str(seconds),str(out)]
    elif system=='Darwin': cmd=['ffmpeg','-y','-f','avfoundation','-i',':0','-t',str(seconds),str(out)]
    else: cmd=['ffmpeg','-y','-f','pulse','-i','default','-t',str(seconds),str(out)]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=seconds+20)
    if result.returncode: raise RuntimeError(result.stderr[-1000:])
    return 'Recorded '+str(out)
