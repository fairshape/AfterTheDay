from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.infrastructure.media.storage import AUDIO_LIMIT, PHOTO_LIMIT
from app.services.anniversaries import MOODS, tags
from app.services.diary import MAX_PHOTOS, MAX_STORY, DraftError
from app.services.music import track_link
from app.web.routes.diary import diary_for, media_url, owner_for, public_track

router = APIRouter(prefix="/api/capture")


def payload(day):
    return {
        "id": day.id,
        "revision": day.revision,
        "story": day.story,
        "date": day.memory_date.isoformat(),
        "title": day.details.get("custom_title", ""),
        "reflection": day.details.get("reflection", ""),
        "moods": day.mood_tags,
        "suggestions": tags(day),
        "coverPhoto": day.details.get("cover_photo"),
        "options": list(MOODS),
        "track": public_track(day, day.track),
        "photos": [{"id": p["id"], "src": media_url(day, p["id"])} for p in day.photos],
    }


@router.post("")
def resume(owner=Depends(owner_for), diary=Depends(diary_for)):
    return payload(diary.draft(owner, create=True))


class Fields(BaseModel):
    revision: int
    story: str = Field(max_length=MAX_STORY)
    date: date
    title: str = Field(max_length=90)
    reflection: str = Field(max_length=360)
    coverPhoto: str | None = Field(default=None, max_length=32)
    moods: list[str] | None = Field(default=None, max_length=8)
    order: list[str] = Field(max_length=MAX_PHOTOS)
    link: str = Field(default="", max_length=2048)
    profile: Literal["calm", "rhythmic", "tense", "rising"] = "calm"


def current(diary, owner, id, revision):
    day = diary.get(owner, str(id), include_draft=True)
    if not day or day.saved_at:
        raise HTTPException(404, "draft")
    if day.revision != revision:
        raise HTTPException(409, "stale")
    return day


@router.post("/{id}/fields")
def fields(id: UUID, body: Fields, owner=Depends(owner_for), diary=Depends(diary_for)):
    day = current(diary, owner, id, body.revision)
    if (
        set(body.moods or []) - MOODS.keys()
        or set(body.order) != {p["id"] for p in day.photos}
        or len(body.order) != len(day.photos)
    ):
        raise HTTPException(422, "invalid_selection")
    details = {**day.details, "custom_title": body.title.strip(), "reflection": body.reflection.strip()}
    if "coverPhoto" in body.model_fields_set:
        if body.coverPhoto and body.coverPhoto not in body.order:
            raise HTTPException(422, "cover_photo")
        details["cover_photo"] = body.coverPhoto
    if body.date != day.memory_date:
        details["event_date"] = body.date.isoformat()
    track = dict(day.track)
    if body.link and body.link != track.get("url"):
        url = track_link(body.link.strip())
        if not url:
            raise HTTPException(422, "link")
        track = {"kind": "link", "url": url, "title": "Песня по ссылке"}
    if track and (not track.get("profile") or body.profile != track.get("profile")):
        track.update(profile=body.profile, signal="user")
    if track and "signal" not in track:
        track["signal"] = "user"
    photos = {p["id"]: p for p in day.photos}
    try:
        diary.edit(
            day,
            story=body.story,
            details=details,
            memory_date=body.date,
            mood_tags=body.moods,
            photos=[photos[id] for id in body.order],
            track=track,
        )
    except DraftError as exc:
        raise HTTPException(409, str(exc)) from exc
    return payload(day)


@router.post("/{id}/remove/{photo}")
def remove(id: UUID, photo: str, revision: int, owner=Depends(owner_for), diary=Depends(diary_for)):
    day = current(diary, owner, id, revision)
    try:
        diary.remove_photo(day, photo)
    except DraftError as exc:
        raise HTTPException(409, str(exc)) from exc
    return payload(day)


@router.post("/{id}/upload/{kind}")
async def upload(
    id: UUID,
    kind: Literal["photo", "audio"],
    revision: int,
    request: Request,
    owner=Depends(owner_for),
    diary=Depends(diary_for),
):
    day = await run_in_threadpool(current, diary, owner, id, revision)
    limit = PHOTO_LIMIT if kind == "photo" else AUDIO_LIMIT
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > limit:
            raise HTTPException(413, "file_size")
        data.extend(chunk)
    try:
        if kind == "photo":
            await run_in_threadpool(diary.add_photo, day, bytes(data), "")
        else:
            await run_in_threadpool(
                diary.set_track, day, {"kind": "file", "title": "Моя дорожка"}, bytes(data)
            )
    except DraftError as exc:
        raise HTTPException(409 if str(exc) == "stale" else 422, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return payload(day)
