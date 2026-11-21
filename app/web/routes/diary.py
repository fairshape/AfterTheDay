from typing import Annotated
from uuid import UUID

from fastapi import BackgroundTasks, APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.db.models import Day, UserPreference
from app.infrastructure.media.previews import photo_preview
from app.services.studio import StudioChoices
from app.services.emotion import memory_art
from app.services.art_direction import original_cover, suggest_color
from app.services.anniversaries import MOODS, tags
from app.services.context import visible_place
from app.services.narration import assets_for, scene_key, suggested_rate
from app.services.voice_workflow import preview_voice, save_voice
from app.services.diary import Diary, DraftError
from app.web.routes.demo import COOKIE, browser_owner
from app.web.auth import SESSION_TTL, TelegramAuth

router = APIRouter(prefix="/api")
NO_CACHE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class TelegramLogin(BaseModel):
    initData: str = Field(max_length=8192)


class PinRequest(BaseModel):
    photo: str | None = Field(default=None, max_length=32)
    quote: str | None = Field(default=None, max_length=108)


class ScenePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    photo: str | None = Field(default=None, max_length=32)
    quote: str | None = Field(default=None, max_length=108)
    cue: float | None = Field(default=None, ge=0, le=7200)
    captions: dict[Annotated[str, Field(pattern=r"^[a-f0-9]{32}:[01]$")], Annotated[str, Field(max_length=108)]] = Field(default_factory=dict, max_length=10)
    resetCaptions: bool = False
    studio: StudioChoices | None = None


class ConfirmSceneRequest(BaseModel):
    token: str = Field(pattern=r"^[a-f0-9]{32}$")


class VoicePreviewRequest(BaseModel):
    voice: str = Field(pattern=r"^(irina|denis)$")
    rate: str = Field(pattern=r"^(slow|normal|lively)$")


class CoverStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: str = Field(max_length=24)
    sticker: str = Field(max_length=24)
    photo: str = Field(max_length=32)


class CoverRequest(BaseModel):
    revision: int | None = Field(default=None, ge=0)
    previewToken: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    mainPhoto: str | None = Field(default=None, max_length=32)
    voice: VoicePreviewRequest | None = None
    moods: list[str] | None = Field(default=None, max_length=len(MOODS))
    style: CoverStyle | None


def diary_for(request: Request) -> Diary:
    return request.app.state.diary


def owner_for(request: Request, authorization: str = Header(default="")) -> int:
    auth: TelegramAuth | None = request.app.state.auth
    if auth is None:
        owner = browser_owner(request.cookies.get(COOKIE, ""))
        with request.app.state.diary.sessions() as db:
            if not db.get(UserPreference, owner):
                raise HTTPException(401, "demo_session")
        return owner
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
def session(body: TelegramLogin, request: Request, response: Response):
    auth: TelegramAuth | None = request.app.state.auth
    if auth is None:
        raise HTTPException(404, "unavailable")
    try:
        token = auth.issue(auth.verify_init_data(body.initData))
        response.set_cookie("memory_media", token, max_age=SESSION_TTL, path="/api/days/", httponly=True,
                            secure=request.url.scheme == "https", samesite="strict")
        return {"token": token}
    except ValueError as exc:
        raise HTTPException(401, "login") from exc


def media_url(day: Day, asset_id: str) -> str:
    return f"/api/days/{day.id}/media/{asset_id}"


def public_track(day: Day, track: dict) -> dict:
    keys = ("kind", "title", "url", "duration", "cue", "artist", "album", "provider", "track_id", "genre", "year", "metadataSource", "profile", "signal")
    result = {key: track[key] for key in keys if key in track}
    if track.get("id"):
        result["asset"] = media_url(day, track["id"])
    return result


def public_scene(day: Day, scene: dict) -> dict:
    result = {**scene, "track": public_track(day, scene["track"]), "narrationKey": scene_key(scene)}
    for key in ("frames", "evenFrames"):
        if key in scene:
            result[key] = [{**frame, "asset": media_url(day, frame["asset"])} for frame in scene[key]]
    return result


def card(day: Day, scene: dict | None = None) -> dict:
    scene = scene or day.scene
    style = day.cover_style or original_cover(day, scene)
    return {"id": day.id, "title": day.title or scene["title"], "date": day.memory_date.isoformat(),
            "emotion": memory_art(day, scene), "photoCount": len(day.photos),
            "focus": scene.get("signals", {}).get("story", ""),
            "opening": scene.get("signals", {}).get("opening", ""),
            "stills": [media_url(day, item["id"]) for item in day.photos[:3]],
            "duration": scene.get("soundtrack", {}).get("duration") or sum(frame["seconds"] for frame in scene["frames"]),
            "trackLabel": day.track.get("title",""), "audioFile": day.track.get("kind")=="file",
            "favorite": day.favorite, "moods": tags(day), "moodsConfirmed": day.mood_tags is not None,
            "cover": media_url(day, style["photo"]), "style": style, "place": visible_place(day.details),
            "coverPalette": scene["palette"] if scene.get("palette", {}).get("field") else None}


def narration_payload(day: Day, value: dict) -> dict:
    payload = {key: item for key, item in value.items() if key != "storyHash"}
    for key in ("full", "mix", "voiceOnly"):
        if key in payload:
            item = payload[key]
            payload[key] = {"asset": media_url(day, item["id"]), "duration": item.get("duration")}
    return payload


def folder(day: Day, candidate: dict | None = None) -> dict:
    scene = candidate["scene"] if candidate else day.scene
    comparison = candidate["comparison"] if candidate else day.comparison
    spoken = candidate.get("narration", day.narration) if candidate else day.narration
    details = candidate["details"] if candidate else day.details
    track = candidate["track"] if candidate else day.track
    details = {key: value for key, value in details.items() if key != "coordinates" and not key.startswith("_")}
    if "place" in details:
        details["place"] = visible_place(details)
    return {
        **card(day, scene), "originalStyle": original_cover(day, scene), "photoColor": suggest_color(day, scene),
        "revision": day.revision, "moodOptions": list(MOODS), "story": day.story, "details": details, "track": public_track(day, track),
        "photos": [{"id": photo["id"], "src": media_url(day, photo["id"]), "caption": photo["caption"]}
                   for photo in day.photos],
        "scene": public_scene(day, scene), "comparison": public_scene(day, comparison) if comparison else None,
        "narration": narration_payload(day, spoken),
        "voiceSuggestion": suggested_rate(day, scene),
        "draft": day.saved_at is None, "previewToken": candidate["token"] if candidate else None,
    }


@router.get("/days")
def archive(q: str = Query(default="", max_length=120), owner: int = Depends(owner_for),
            diary: Diary = Depends(diary_for)):
    return [card(day) for day in diary.archive(owner, q)]


def media_owner(request: Request, authorization: str = Header(default="")) -> int:
    auth = request.app.state.auth
    if auth and not authorization:
        try:
            return auth.verify_session(request.cookies.get("memory_media", ""))
        except ValueError as exc:
            raise HTTPException(401, "media_login") from exc
    return owner_for(request, authorization)


@router.get("/days/media-session")
def media_session(request: Request, owner: int = Depends(owner_for)):
    try:
        return {"direct": media_owner(request, "") == owner}
    except HTTPException:
        return {"direct": False}


@router.get("/days/{day_id}")
def get_day(day_id: UUID, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
    return folder(day)


@router.post("/days/{day_id}/cover")
def cover(day_id: UUID, body: CoverRequest, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    if (body.voice or "mainPhoto" in body.model_fields_set) and body.revision is None:
        raise HTTPException(422, "revision_required")
    try:
        choices = {"photo": body.mainPhoto} if "mainPhoto" in body.model_fields_set else {}
        day = diary.set_cover(owner, str(day_id), body.style.model_dump() if body.style else {}, body.moods,
                              choices=choices, voice=body.voice.model_dump() if body.voice else None,
                              revision=body.revision, preview_token=body.previewToken)
        return folder(day, None if day.saved_at else day.scene_preview)
    except DraftError as exc:
        status = {"missing_day": 404, "invalid_pin": 422, "invalid_cover": 422, "stale": 409, "speech_unavailable": 503}.get(str(exc), 422)
        raise HTTPException(status, str(exc)) from exc

    except SpeechUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc


@router.post("/days/{day_id}/scene/preview")
def scene_preview(day_id: UUID, body: ScenePreviewRequest, request: Request, background: BackgroundTasks, owner: int = Depends(owner_for),
                  diary: Diary = Depends(diary_for)):
    try:
        assembly = getattr(request.app.state, "notify_assembly", None)
        before = diary.get(owner, str(day_id), include_draft=True) if assembly else None
        day, candidate = diary.preview_scene(owner, str(day_id), body.model_dump(exclude_unset=True))
        if before and not before.saved_at and before.scene_preview.get("revision") != before.revision:
            background.add_task(assembly, owner)
        return folder(day, candidate)
    except DraftError as exc:
        status = 404 if str(exc) == "missing_day" else 409 if str(exc) in {"stale", "incomplete"} else 422
        raise HTTPException(status, str(exc)) from exc
    except SpeechUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "asset_unavailable") from exc


@router.post("/days/{day_id}/scene/confirm")
async def confirm_preview(day_id: UUID, body: ConfirmSceneRequest, request: Request, owner: int = Depends(owner_for),
                          diary: Diary = Depends(diary_for)):
    try:
        day, published = await run_in_threadpool(diary.commit_preview, owner, str(day_id), body.token)
        notify = getattr(request.app.state, "notify_publication", None)
        if published and notify:
            await notify(day)
        return folder(day)
    except DraftError as exc:
        raise HTTPException(404 if str(exc) == "missing_day" else 409, str(exc)) from exc


@router.get("/voices")
def available_voices(_owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    return {"voices": diary.voice.provider.available() if diary.voice else []}


@router.post("/days/{day_id}/voice/preview")
def create_voice_preview(day_id: UUID, body: VoicePreviewRequest, owner: int = Depends(owner_for),
                         diary: Diary = Depends(diary_for)):
    try:
        day, candidate = preview_voice(diary, owner, str(day_id), body.voice, body.rate)
        return {"token": candidate["token"], "audio": media_url(day, candidate["sample"]["id"]),
                "duration": candidate["sample"]["duration"]}
    except DraftError as exc:
        raise HTTPException(404 if str(exc) == "missing_day" else 409, str(exc)) from exc
    except SpeechUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc


@router.post("/days/{day_id}/voice/confirm")
def confirm_voice(day_id: UUID, body: ConfirmSceneRequest, owner: int = Depends(owner_for),
                  diary: Diary = Depends(diary_for)):
    try:
        day = save_voice(diary, owner, str(day_id), body.token)
        return folder(day, None if day.saved_at else day.scene_preview)
    except DraftError as exc:
        raise HTTPException(404 if str(exc) == "missing_day" else 409, str(exc)) from exc
    except SpeechUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc


@router.post("/days/{day_id}/pin")
def pin(day_id: UUID, body: PinRequest, owner: int = Depends(owner_for), diary: Diary = Depends(diary_for)):
    if not diary.get(owner, str(day_id)):
        raise HTTPException(404, "day")
    try:
        day = diary.pin(owner, str(day_id), body.photo, body.quote)
    except DraftError as exc:
        raise HTTPException(409 if str(exc) == "stale" else 422, str(exc)) from exc
    except SpeechUnavailable as exc:
        raise HTTPException(503, "speech_unavailable") from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "asset_unavailable") from exc
    return folder(day)


@router.get("/days/{day_id}/media/{asset_id}")
def media(day_id: UUID, asset_id: str, owner: int = Depends(media_owner), diary: Diary = Depends(diary_for),
          *, preview: bool = False):
    day = diary.get(owner, str(day_id), include_draft=True)
    if day is None:
        raise HTTPException(404, "asset")
    assets = [*day.photos, day.track, day.scene_preview.get("track", {}), *day.details.get("_previous_audio", []), (day.comparison or {}).get("track", {}), *assets_for(day)]
    match = next((asset for asset in assets if asset.get("id") == asset_id), None)
    if match is None:
        raise HTTPException(404, "asset")
    path = diary.media.path(str(day_id), asset_id)
    if not path.is_file():
        raise HTTPException(404, "asset")
    if preview and match["mime"].startswith("image/"):
        try:
            return Response(photo_preview(path, path.stat().st_mtime_ns),
                            media_type="image/webp", headers=NO_CACHE)
        except (OSError, ValueError):
            raise HTTPException(404, "asset")
    return FileResponse(path, media_type=match["mime"], headers=NO_CACHE)
