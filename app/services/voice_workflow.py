"""Owner-scoped voice preview and publication."""
from uuid import uuid4

from sqlalchemy import update

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.db.models import Day
from app.services.diary import Diary, DraftError


def current_scene(day: Day) -> tuple[dict, str | None]:
    if day.saved_at:
        return day.scene, None
    candidate = day.scene_preview
    if candidate.get("revision") != day.revision:
        raise DraftError("incomplete")
    return candidate["scene"], candidate["token"]


def preview_voice(diary: Diary, owner: int, day_id: str, voice: str, rate: str) -> tuple[Day, dict]:
    day = diary.get(owner, day_id, include_draft=True)
    if not day:
        raise DraftError("missing_day")
    _, scene_token = current_scene(day)
    if not diary.voice:
        raise SpeechUnavailable
    sample = diary.voice.sample(day, voice, rate)
    candidate = {"token": uuid4().hex, "revision": day.revision, "sceneToken": scene_token,
                 "voice": voice, "rate": rate, "sample": sample}
    condition = [Day.id == day_id, Day.owner_id == owner, Day.revision == day.revision]
    if scene_token:
        condition.append(Day.scene_preview["token"].as_string() == scene_token)
    with diary.sessions.begin() as session:
        response = session.execute(update(Day).where(*condition).values(voice_preview=candidate))
        if response.rowcount != 1:
            diary.media.remove(day_id, sample["id"])
            raise DraftError("stale")
    old_sample = day.voice_preview.get("sample")
    if old_sample:
        diary.media.remove(day_id, old_sample["id"])
    day.voice_preview = candidate
    return day, candidate


def save_voice(diary: Diary, owner: int, day_id: str, token: str) -> Day:
    day = diary.get(owner, day_id, include_draft=True)
    if not day:
        raise DraftError("missing_day")
    scene, scene_token = current_scene(day)
    pending = day.voice_preview
    if (pending.get("token") != token or pending.get("revision") != day.revision
            or pending.get("sceneToken") != scene_token):
        raise DraftError("stale")
    if not diary.voice:
        raise SpeechUnavailable
    spoken = diary.voice.build(day, scene, pending["voice"], pending["rate"], day.narration)
    changes = {"narration": spoken, "voice_preview": {}}
    condition = [Day.id == day_id, Day.owner_id == owner, Day.revision == day.revision,
                 Day.voice_preview["token"].as_string() == token]
    if scene_token:
        condition.append(Day.scene_preview["token"].as_string() == scene_token)
        changes["scene_preview"] = {**day.scene_preview, "narration": spoken}
    else:
        changes.update(revision=day.revision + 1, scene_preview={})
    with diary.sessions.begin() as session:
        response = session.execute(update(Day).where(*condition).values(**changes))
        if response.rowcount != 1:
            raise DraftError("stale")
    diary.media.remove(day_id, pending["sample"]["id"])
    updated = diary.get(owner, day_id, include_draft=True)
    diary.voice.prune(updated)
    return updated
