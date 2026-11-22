"""Preview a primary or comparison soundtrack before publishing it."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.media.storage import AUDIO_LIMIT
from app.services.diary import DraftError
from app.services.music import PROFILES, URL_PATTERN, track_link
from app.web.routes.diary import diary_for, folder, owner_for

router = APIRouter(prefix="/api/days")
TrackSlot = Literal["primary", "alternate"]


class Link(BaseModel):
    url: str = Field(max_length=4096)
    profile: str = Field(max_length=12)


def remix(diary, owner, day_id, track, data=None, *, slot: TrackSlot = "primary", revision: int | None = None):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
    if revision is not None and revision != day.revision:
        raise HTTPException(409, "stale")
    if track["profile"] not in PROFILES:
        raise HTTPException(422, "profile")
    new_file = None
    try:
        if data is not None:
            new_file = diary.media.ingest(day.id, data, "audio")
            track.update(new_file)
        choice = "alternate_track" if slot == "alternate" else "replacement"
        day, candidate = diary.preview_scene(owner, day.id, {choice: track, "revision": day.revision})
    except (ValueError, OSError, SpeechUnavailable) as exc:
        if new_file:
            diary.media.remove(day.id, new_file["id"])
        if isinstance(exc, DraftError):
            raise HTTPException(409, str(exc)) from exc
        if isinstance(exc, SpeechUnavailable):
            raise HTTPException(503, "speech_unavailable") from exc
        if isinstance(exc, OSError):
            raise HTTPException(409, "asset_unavailable") from exc
        raise HTTPException(422, "audio_format") from exc
    return folder(day, candidate)


@router.post("/{day_id}/music/link")
def change_link(
    day_id: UUID, selection: Link, owner=Depends(owner_for), diary=Depends(diary_for),
    slot: TrackSlot = "primary", revision: int | None = None,
):
    value = selection.url.strip()
    found = URL_PATTERN.findall(value)
    url = track_link(value) or (track_link(found[0]) if len(found) == 1 else None)
    if not found and "/" in value:
        url = track_link("https://" + value)
    if url is None:
        raise HTTPException(422, "link")
    return remix(
        diary,
        owner,
        day_id,
        {
            "kind": "link",
            "url": url,
            "profile": selection.profile,
            "title": "Вторая песня по ссылке" if slot == "alternate" else "Песня по ссылке",
            "signal": "user",
        }, slot=slot, revision=revision,
    )


@router.post("/{day_id}/music/file")
async def change_file(
    day_id: UUID, profile: str, request: Request, owner=Depends(owner_for), diary=Depends(diary_for),
    slot: TrackSlot = "primary", name: str = Query(default="", max_length=160), revision: int | None = None,
):
    day = await run_in_threadpool(diary.get, owner, str(day_id))
    if not day:
        raise HTTPException(404, "day")
    if revision is not None and day.revision != revision:
        raise HTTPException(409, "stale")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > AUDIO_LIMIT:
            raise HTTPException(413, "file_size")
        data.extend(chunk)
    title = name.strip() or ("Вторая дорожка" if slot == "alternate" else "Моя дорожка")
    return await run_in_threadpool(
        remix,
        diary,
        owner,
        day_id,
        {"kind": "file", "profile": profile, "title": title, "signal": "user"},
        bytes(data),
        slot=slot, revision=day.revision,
    )
