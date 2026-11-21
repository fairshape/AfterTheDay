from io import BytesIO
import re
import wave
from urllib.parse import urlsplit

import mutagen

AUDIO_TYPES = {"MP3": "audio/mpeg", "MP4": "audio/mp4", "OggOpus": "audio/ogg",
               "OggVorbis": "audio/ogg", "FLAC": "audio/flac", "WAVE": "audio/wav"}
PROFILES = {"calm", "rhythmic", "tense", "rising"}
URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def track_link(value: str) -> str | None:
    if not URL_PATTERN.fullmatch(value) or len(value) > 1800 or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid_host = parsed.hostname and "." in parsed.hostname and parsed.username is None
        if parsed.scheme in {"https", "http"} and valid_host and (port is None or 1 <= port <= 65535):
            return value if parsed.path.strip("/") and not any(ord(character) < 32 for character in value) else None
    except ValueError:
        pass
    return None


def inspect_audio(data: bytes) -> dict:
    try:
        audio = mutagen.File(BytesIO(data))
        mime = AUDIO_TYPES.get(type(audio).__name__)
        duration = float(audio.info.length) if mime else 0
        if not 1 <= duration <= 7200:
            raise ValueError
        if mime == "audio/mp4" and audio.info.codec not in {"mp4a.40.2", "mp4a.40.5", "mp4a.40.29"}:
            raise ValueError
        if mime == "audio/wav":
            with wave.open(BytesIO(data)) as wav:
                if wav.getnchannels() not in {1, 2} or wav.getsampwidth() not in {1, 2, 3, 4}:
                    raise ValueError
                if len(wav.readframes(wav.getnframes())) != wav.getnframes() * wav.getsampwidth() * wav.getnchannels():
                    raise ValueError
    except (mutagen.MutagenError, ValueError, OSError, EOFError, wave.Error, OverflowError) as exc:
        raise ValueError("audio_format") from exc

    metadata = {"mime": mime, "duration": round(duration, 3)}
    try:
        normalized = mutagen.File(BytesIO(data), easy=True)
        if normalized and normalized.tags:
            for target, tag in (("title", "title"), ("artist", "artist"), ("album", "album"), ("genre", "genre")):
                values = normalized.get(tag, [])
                if values:
                    metadata[target] = str(values[0]).strip()[:160]
            values = normalized.get("date", [])
            if values and re.fullmatch(r"\d{4}", str(values[0])[:4]):
                metadata["year"] = str(values[0])[:4]
            if len(metadata) > 2:
                metadata["metadataSource"] = "file_tags"
    except (mutagen.MutagenError, ValueError, OSError, EOFError):
        pass
    return metadata
