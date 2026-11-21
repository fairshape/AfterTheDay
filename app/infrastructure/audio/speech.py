from dataclasses import dataclass
from importlib.util import find_spec
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
import wave

from app.infrastructure.audio.analysis import DEMUXERS
from config.settings import ROOT

RATES = {"slow": .85, "normal": 1.0, "lively": 1.15}
MAX_STORY_WAV = 80 * 1024 * 1024
DUCK_GAIN = .28
DUCK_FADE = .17
WORKERS = BoundedSemaphore(2)


class SpeechUnavailable(Exception):
    pass


@dataclass(frozen=True)
class SpeechClip:
    wav: bytes
    pcm: bytes
    rate: int

    @property
    def seconds(self) -> float:
        return len(self.pcm) / (2 * self.rate)


class PiperSpeech:
    def __init__(self, directory: Path, voices: dict[str, str], timeout: float):
        self.directory = directory
        self.models = voices
        self.timeout = timeout

    def available(self) -> list[str]:
        return [name for name, model in self.models.items() if find_spec("piper")
                and (self.directory / f"{model}.onnx").is_file()
                and (self.directory / f"{model}.onnx.json").is_file()]

    def synthesize(self, voice: str, rate: str, texts: list[str]) -> list[SpeechClip]:
        if voice not in self.available() or rate not in RATES or not WORKERS.acquire(timeout=1):
            raise SpeechUnavailable
        try:
            with TemporaryDirectory(prefix="after-day-speech-") as location:
                model = self.directory / f"{self.models[voice]}.onnx"
                subprocess.run([sys.executable, "-m", "app.infrastructure.audio.speech_worker",
                                str(model), location], cwd=ROOT,
                               input=json.dumps({"rate": RATES[rate], "texts": texts}).encode(),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               env={**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1"},
                               timeout=self.timeout, check=True)
                clips = []
                for index in range(len(texts)):
                    path = Path(location) / f"{index}.wav"
                    if not 0 < path.stat().st_size <= MAX_STORY_WAV:
                        raise SpeechUnavailable
                    raw = path.read_bytes()
                    with wave.open(BytesIO(raw)) as audio:
                        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getnframes() < 1:
                            raise SpeechUnavailable
                        clips.append(SpeechClip(raw, audio.readframes(audio.getnframes()), audio.getframerate()))
                return clips
        except (OSError, subprocess.SubprocessError, wave.Error, EOFError) as exc:
            raise SpeechUnavailable from exc
        finally:
            WORKERS.release()


def scene_mix(voice: bytes, track: Path, mime: str, offset: float, seconds: float, windows: list[dict]) -> bytes:
    demuxer = DEMUXERS.get(mime)
    if not demuxer:
        raise SpeechUnavailable
    # A single server-rendered mix keeps seeking and gain changes reliable in mobile webviews.
    terms = []
    depth = 1 - DUCK_GAIN
    for window in windows:
        beginning, end = window["start"], window["start"] + window["duration"]
        terms.append(f"{depth}*max(0,min(1,min((t-{beginning-DUCK_FADE:.3f})/{DUCK_FADE},"
                     f"({end+DUCK_FADE:.3f}-t)/{DUCK_FADE})))")
    gain = f".78*(1-min({depth},({'+'.join(terms)})))"
    filters = (f"[0:a]asetpts=PTS-STARTPTS,apad,volume='{gain}':eval=frame[music];"
               "[1:a]volume=.94[voice];[music][voice]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=.94:latency=1")
    try:
        output = subprocess.run([
            "ffmpeg", "-v", "error", "-threads", "1", "-protocol_whitelist", "file,pipe",
            *([] if demuxer != "mov" else ["-enable_drefs", "0", "-use_absolute_path", "0"]),
            "-ss", str(offset), "-f", demuxer, "-i", str(track), "-f", "wav", "-i", "pipe:0",
            "-filter_complex_threads", "1", "-filter_complex", filters, "-t", str(seconds),
            "-ac", "2", "-ar", "44100", "-codec:a", "pcm_s16le", "-f", "s16le", "pipe:1",
        ], input=voice, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SpeechUnavailable from exc
    pcm = output.stdout
    if not pcm:
        raise SpeechUnavailable
    wave_file = BytesIO()
    with wave.open(wave_file, "wb") as audio:
        audio.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        audio.writeframes(pcm)
    return wave_file.getvalue()
