"""Build a replacement soundtrack as a preview before touching the published day."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.media.storage import AUDIO_LIMIT
from app.services.diary import DraftError
from app.services.music import PROFILES, track_link
from app.web.routes.diary import diary_for, folder, owner_for

router = APIRouter(prefix="/api/days")


class Link(BaseModel):
    url: str = Field(max_length=1800)
    profile: str = Field(max_length=12)


def remix(diary, owner, day_id, track, data=None):
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
        day, candidate = diary.preview_scene(
            owner, day.id, {"replacement": track, "revision": day.revision}
        )
    except (ValueError, OSError, SpeechUnavailable) as exc:
        if new_file:
            diary.media.remove(day.id, new_file["id"])
        raise HTTPException(409 if isinstance(exc, DraftError) else 422, "music_preview_failed") from exc
    return folder(day, candidate)


@router.post("/{day_id}/music/link")
def change_link(day_id: UUID, selection: Link, owner=Depends(owner_for), diary=Depends(diary_for)):
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
            "title": "Песня по ссылке",
            "signal": "user",
        },
    )


@router.post("/{day_id}/music/file")
async def change_file(
    day_id: UUID, profile: str, request: Request, owner=Depends(owner_for), diary=Depends(diary_for)
):
    if not await run_in_threadpool(diary.get, owner, str(day_id)):
        raise HTTPException(404, "day")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > AUDIO_LIMIT:
            raise HTTPException(413, "file_size")
        data.extend(chunk)
    return await run_in_threadpool(
        remix,
        diary,
        owner,
        day_id,
        {"kind": "file", "profile": profile, "title": "Моя дорожка", "signal": "user"},
        bytes(data),
    )
