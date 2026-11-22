"""Preview a primary or comparison soundtrack before publishing it."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.media.storage import AUDIO_LIMIT
from app.services.diary import DraftError
from app.services.music import PROFILES, track_link
from app.web.routes.diary import diary_for, folder, owner_for

router = APIRouter(prefix="/api/days")
TrackSlot = Literal["primary", "alternate"]


class Link(BaseModel):
    url: str = Field(max_length=1800)
    profile: str = Field(max_length=12)


def remix(diary, owner, day_id, track, data=None, *, slot: TrackSlot = "primary"):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
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
        raise HTTPException(409 if isinstance(exc, DraftError) else 422, "music_preview_failed") from exc
    return folder(day, candidate)


@router.post("/{day_id}/music/link")
def change_link(
    day_id: UUID, selection: Link, owner=Depends(owner_for), diary=Depends(diary_for),
    slot: TrackSlot = "primary",
):
    url = track_link(selection.url.strip())
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
        }, slot=slot,
    )


@router.post("/{day_id}/music/file")
async def change_file(
    day_id: UUID, profile: str, request: Request, owner=Depends(owner_for), diary=Depends(diary_for),
    slot: TrackSlot = "primary", name: str = Query(default="", max_length=160),
):
    if not await run_in_threadpool(diary.get, owner, str(day_id)):
        raise HTTPException(404, "day")
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
        slot=slot,
    )
