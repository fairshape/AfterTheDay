from hashlib import sha256
from io import BytesIO
import json
import re
from time import time
import wave

from app.infrastructure.audio.speech import DUCK_FADE, DUCK_GAIN, PiperSpeech, SpeechUnavailable
from app.infrastructure.db.models import Day
from app.infrastructure.media.storage import MediaStore
from app.services.story import interpret


def scene_key(scene: dict) -> str:
    track = scene.get("track", {})
    value = [scene.get("frames"), track.get("id"), track.get("cue"), scene.get("soundtrack")]
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def assets_for(day: Day) -> list[dict]:
    assets = [day.voice_preview.get("sample", {})]
    for narration in (day.narration, day.scene_preview.get("narration", {})):
        assets.extend(narration[key] for key in ("full", "voiceOnly", "mix") if narration.get(key))
    return assets


def suggested_rate(day: Day, scene: dict) -> str:
    arc = interpret(day.story, day.details)
    if arc.quiet or (arc.intimate and scene.get("signals", {}).get("profile") == "calm"):
        return "slow"
    if re.search(r"смех|смеял|расхохотал|весел|танцевал|бодр", f"{day.story} {day.details.get('mood', '')}", re.I):
        return "lively"
    return "normal"


class Narration:
    def __init__(self, media: MediaStore, provider: PiperSpeech):
        self.media = media
        self.provider = provider

    def sample(self, day: Day, voice: str, rate: str) -> dict:
        arc = interpret(day.story, day.details)
        phrase = arc.opening or day.story[:108]
        clip, = self.provider.synthesize(voice, rate, [phrase])
        return self.media.write(day.id, clip.wav, {"mime": "audio/wav", "duration": round(clip.seconds, 3)}, generated=True)

    def build(self, day: Day, scene: dict, voice: str, rate: str, existing: dict) -> dict:
        from app.infrastructure.audio.speech import scene_mix

        track = scene["track"]
        total = scene.get("soundtrack", {}).get("duration", sum(frame["seconds"] for frame in scene["frames"]))
        offset = scene.get("soundtrack", {}).get("offset", track.get("cue", 0))
        original = " ".join(day.story.casefold().split())
        story_hash = sha256(day.story.encode()).hexdigest()
        key = scene_key(scene)
        same_voice = all(existing.get(field) == value for field, value in (
            ("voice", voice), ("rate", rate), ("storyHash", story_hash)))
        existing_files = [existing[name] for name in ("full", "voiceOnly", "mix") if existing.get(name)]
        if same_voice and existing.get("sceneKey") == key and all(
                self.media.path(day.id, item["id"]).is_file() for item in existing_files):
            return existing
        full = existing.get("full") if same_voice else None
        if full and not self.media.path(day.id, full["id"]).is_file():
            full = None

        frames = scene["frames"]
        ranges = []
        cursor = 0.0
        for index, frame in enumerate(frames):
            caption = frame["caption"]
            start = frame.get("start", cursor)
            cursor = start + frame["seconds"]
            spoken = caption and " ".join(caption.casefold().split()) in original
            if spoken:
                beginning = start + max(frame.get("captionIn", 0), min(.46, frame["seconds"] * .12))
                ending = start + frame.get("captionOut", frame["seconds"])
                ranges.append((index, caption, beginning, ending))
        if len(ranges) > 3:
            ranges = [ranges[0], ranges[1], ranges[-1]]
        if not ranges:
            opening = interpret(day.story, day.details).opening
            if opening and " ".join(opening.casefold().split()) in original:
                ranges = [(0, opening, .23, total)]

        texts = [caption for _, caption, _, _ in ranges] + ([] if full else [day.story])
        if not texts:
            return existing
        clips = self.provider.synthesize(voice, rate, texts)
        scheduled = []
        for (_, line, start, end), clip in zip(ranges, clips):
            if start + clip.seconds <= end + .002:
                scheduled.append(({"start": round(start, 3), "duration": round(clip.seconds, 3), "text": line}, clip))
        if not scheduled and total >= 2.5:
            phrase = (ranges[-1][1] if ranges else day.story).split()
            text = " ".join(phrase[:min(4, max(2, int(total*.8)))])
            short, = self.provider.synthesize(voice, rate, [text])
            if short.seconds + .3 <= total:
                scheduled.append(({"start": .23, "duration": round(short.seconds, 3), "text": text}, short))

        block = {"voice": voice, "rate": rate, "storyHash": story_hash, "sceneKey": key,
                 "timing": [entry for entry, _ in scheduled]}
        if scheduled:
            rate_hz = scheduled[0][1].rate
            pcm = bytearray(round(total * rate_hz) * 2)
            for entry, clip in scheduled:
                start = round(entry["start"] * rate_hz) * 2
                length = min(len(clip.pcm), len(pcm) - start)
                pcm[start:start+length] = clip.pcm[:length]
            output = BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setparams((1, 2, rate_hz, 0, "NONE", "not compressed"))
                wav.writeframes(pcm)
            voice_audio = output.getvalue()
            if track["kind"] == "file":
                mixed = scene_mix(voice_audio, self.media.path(day.id, track["id"]), track.get("mime", ""),
                                  offset, total, block["timing"])
                block["mix"] = self.media.write(day.id, mixed, {"mime": "audio/wav"}, generated=True)
                block["ducking"] = {"gain": DUCK_GAIN, "fade": DUCK_FADE}
            block["voiceOnly"] = self.media.write(day.id, voice_audio, {"mime": "audio/wav"}, generated=True)
        if not full:
            clip = clips[-1]
            full = self.media.write(day.id, clip.wav, {"mime": "audio/wav", "duration": round(clip.seconds, 3)}, generated=True)
        return {**block, "full": full}

    def prune(self, day: Day) -> None:
        retained = {asset.get("id") for asset in assets_for(day)}
        for path in (self.media.root / day.id).glob("n-*"):
            try:
                if path.name not in retained and time() - path.stat().st_mtime > 600:
                    path.unlink(missing_ok=True)
            except FileNotFoundError:
                continue
