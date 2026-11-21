from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.db.models import Day
from app.services.art_direction import original_cover, suggest_color
from app.services.diary import DEMO_OWNER, Diary, DraftError
from app.web.auth import TelegramAuth

router = APIRouter(prefix="/api")
NO_CACHE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class TelegramLogin(BaseModel):
    initData: str = Field(max_length=8192)


class PinRequest(BaseModel):
    photo: str | None = Field(default=None, max_length=32)
    quote: str | None = Field(default=None, max_length=108)


class CoverStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: str = Field(max_length=24)
    sticker: str = Field(max_length=24)
    photo: str = Field(max_length=32)


class CoverRequest(BaseModel):
    style: CoverStyle | None


def diary_for(request: Request) -> Diary:
    return request.app.state.diary


def owner_for(request: Request, authorization: str = Header(default="")) -> int:
    auth: TelegramAuth | None = request.app.state.auth
    if auth is None:
        return DEMO_OWNER
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(401, "login")
    try:
        return auth.verify_session(token)
    except ValueError as exc:
        raise HTTPException(401, "login") from exc


@router.get("/mode")
def mode(request: Request):
    demo = request.app.state.auth is None
    username = request.app.state.bot_username
    return {"demo": demo, "recordUrl": f"https://t.me/{username}?start=record" if username and not demo else None}


@router.post("/session")
def session(body: TelegramLogin, request: Request):
    auth: TelegramAuth | None = request.app.state.auth
    if auth is None:
        raise HTTPException(404, "unavailable")
    try:
        return {"token": auth.issue(auth.verify_init_data(body.initData))}
    except ValueError as exc:
        raise HTTPException(401, "login") from exc


def media_url(day: Day, asset_id: str) -> str:
    return f"/api/days/{day.id}/media/{asset_id}"


def public_track(day: Day, track: dict) -> dict:
    keys = ("kind", "title", "url", "duration", "cue")
    result = {key: track[key] for key in keys if key in track}
    if track.get("id"):
        result["asset"] = media_url(day, track["id"])
    return result


def public_scene(day: Day, scene: dict) -> dict:
    return {**scene, "track": public_track(day, scene["track"]),
            "frames": [{**frame, "asset": media_url(day, frame["asset"])} for frame in scene["frames"]]}


def card(day: Day) -> dict:
    style = day.cover_style or original_cover(day)
    return {"id": day.id, "title": day.title, "date": day.memory_date.isoformat(),
            "cover": media_url(day, style["photo"]), "style": style, "place": day.details.get("place")}


def folder(day: Day) -> dict:
    return {
        **card(day), "originalStyle": original_cover(day), "photoColor": suggest_color(day), "story": day.story, "details": day.details, "track": public_track(day, day.track),
        "photos": [{"id": photo["id"], "src": media_url(day, photo["id"]), "caption": photo["caption"]}
                   for photo in day.photos],
        "scene": public_scene(day, day.scene),
        "comparison": public_scene(day, day.comparison) if day.comparison else None,
    }


@router.get("/days")
def archive(q: str = Query(default="", max_length=120), owner: int = Depends(owner_for),
            diary: Diary = Depends(diary_for)):
    return [card(day) for day in diary.archive(owner, q)]


@router.get("/days/{day_id}")
def get_day(day_id: UUID, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
    return folder(day)


@router.post("/days/{day_id}/cover")
def cover(day_id: UUID, body: CoverRequest, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    try:
        return folder(diary.set_cover(owner, str(day_id), body.style.model_dump() if body.style else {}))
    except DraftError as exc:
        status = {"missing_day": 404, "invalid_cover": 422, "stale": 409}[str(exc)]
        raise HTTPException(status, str(exc)) from exc


@router.post("/days/{day_id}/pin")
def pin(day_id: UUID, body: PinRequest, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    if not diary.get(owner, str(day_id)):
        raise HTTPException(404, "day")
    try:
        day = diary.pin(owner, str(day_id), body.photo, body.quote)
    except DraftError as exc:
        raise HTTPException(409 if str(exc) == "stale" else 422, str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "asset_unavailable") from exc
    return folder(day)


@router.get("/days/{day_id}/media/{asset_id}")
def media(day_id: UUID, asset_id: str, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "asset")
    assets = [*day.photos, day.track, (day.comparison or {}).get("track", {})]
    match = next((asset for asset in assets if asset.get("id") == asset_id), None)
    if match is None:
        raise HTTPException(404, "asset")
    path = diary.media.path(str(day_id), asset_id)
    if not path.is_file():
        raise HTTPException(404, "asset")
    return FileResponse(path, media_type=match["mime"], headers=NO_CACHE)
