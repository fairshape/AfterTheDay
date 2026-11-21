"""Bounded local waveform analysis. Phrase candidates are changes in smoothed energy."""
from array import array
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from statistics import median
import subprocess
import sys

SAMPLE_RATE = 8000
HOP = .025
BLOCK = int(SAMPLE_RATE * HOP)
ANALYSIS_SECONDS = 75
DECODE_TIMEOUT = 6
DEMUXERS = {"audio/mpeg": "mp3", "audio/mp4": "mov", "audio/ogg": "ogg",
            "audio/flac": "flac", "audio/wav": "wav"}


@dataclass(frozen=True)
class AudioCue:
    at: float
    score: float
    kind: str


@dataclass(frozen=True)
class AudioAnalysis:
    start: float
    energy: tuple[float, ...]
    cues: tuple[AudioCue, ...]
    tempo: float | None
    confidence: float

    def energy_at(self, time: float) -> float:
        return self.energy[min(len(self.energy) - 1, max(0, round((time - self.start) / HOP)))]


def analyze_audio(path: Path, mime: str, start: float = 0) -> AudioAnalysis | None:
    demuxer = DEMUXERS.get(mime)
    if not demuxer or not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
        return None
    try:
        decoded = subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-threads", "1", "-protocol_whitelist", "file,pipe",
            *([] if demuxer != "mov" else ["-enable_drefs", "0", "-use_absolute_path", "0"]),
            "-f", demuxer, "-ss", str(start), "-i", str(path), "-t", str(ANALYSIS_SECONDS),
            "-map", "0:a:0", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1",
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=DECODE_TIMEOUT, check=True)
    except (OSError, subprocess.SubprocessError):
        return None

    waveform = array("h")
    waveform.frombytes(decoded.stdout)
    if sys.byteorder != "little":
        waveform.byteswap()
    energy, texture = [], []
    for start_sample in range(0, len(waveform) - BLOCK + 1, BLOCK):
        samples = waveform[start_sample:start_sample + BLOCK]
        energy.append(sqrt(sum(value * value for value in samples) / BLOCK) / 32768)
        texture.append(sqrt(sum((a-b)**2 for a,b in zip(samples, samples[1:])) / BLOCK) / 32768)
    if len(energy) < 12 or max(energy) < .002:
        return None
    scale = max(sorted(energy)[int(len(energy)*.95)], .003)
    envelope = tuple(min(2, sum(energy[max(0,i-4):i+1]) / min(i+1,5) / scale) for i in range(len(energy)))
    flux = [0.0] + [max(0, (energy[i]-energy[i-1]) + (texture[i]-texture[i-1]) * .65) / scale
                    for i in range(1,len(energy))]
    cutoff = max(.085, median(flux) * 4)
    raw = [AudioCue(round(start+i*HOP, 3), min(1, flux[i]), "onset")
           for i in range(1,len(flux)-1) if flux[i] >= cutoff and flux[i] > flux[i-1] and flux[i] >= flux[i+1]]
    cues: list[AudioCue] = []
    for cue in raw:
        if cues and cue.at - cues[-1].at < .115:
            if cue.score > cues[-1].score:
                cues[-1] = cue
        else:
            cues.append(cue)
    for i in range(12, len(envelope)-12, 6):
        delta = sum(envelope[i:i+12])/12 - sum(envelope[i-12:i])/12
        if abs(delta) > .4 and all(abs(start+i*HOP-cue.at) > .18 for cue in cues):
            cues.append(AudioCue(round(start+i*HOP, 3), min(.7, abs(delta)*.66), "energy_rise" if delta > 0 else "energy_drop"))
    cues.sort(key=lambda cue: cue.at)

    tempo = None
    confidence = 0.0
    if len(raw) >= 5:
        norm = sum(value**2 for value in flux)
        lag, agreement = max(((lag, sum(a*b for a,b in zip(flux, flux[lag:]))/norm)
                              for lag in range(12, 41)), key=lambda pair: pair[1])
        confidence = round(agreement, 3)
        if confidence >= .18:
            tempo = round(60/(lag*HOP), 1)
    return AudioAnalysis(start, envelope, tuple(cues), tempo, confidence)
