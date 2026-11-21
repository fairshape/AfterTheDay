"""Give each browser a separate demo library with hard links to the sample media."""

from hashlib import sha256
from os import link
from secrets import token_urlsafe
from shutil import rmtree
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func, select, text

from app.infrastructure.db.models import Day, UserPreference
from app.services.diary import DEMO_OWNER
from demo.seed import EXAMPLES

router = APIRouter(prefix="/api/demo")
COOKIE = "memory_demo"
MAX_LIBRARIES = 250


def browser_owner(token: str) -> int:
    if len(token) != 43 or not token.isascii():
        raise HTTPException(401, "demo_session")
    return -int.from_bytes(sha256(token.encode()).digest()[:7], "big") - 1


@router.post("/start")
def start_demo(request: Request, response: Response):
    if request.app.state.auth:
        raise HTTPException(404, "demo")
    diary = request.app.state.diary
    token = request.cookies.get(COOKIE, "")
    if token:
        owner = browser_owner(token)
        with diary.sessions() as db:
            if db.get(UserPreference, owner):
                return {"ready": True}
    token = token_urlsafe(32)
    owner = browser_owner(token)
    directories = []
    stories = [example["story"] for example in EXAMPLES]
    try:
        with diary.sessions.begin() as db:
            db.execute(text("BEGIN IMMEDIATE"))
            if (
                db.scalar(
                    select(func.count()).select_from(UserPreference).where(UserPreference.owner_id < 0)
                )
                >= MAX_LIBRARIES
            ):
                raise HTTPException(503, "demo_capacity")
            db.add(UserPreference(owner_id=owner, timezone=str(diary.timezone)))
            for source in db.scalars(
                select(Day).where(
                    Day.owner_id == DEMO_OWNER, Day.story.in_(stories), Day.saved_at.is_not(None)
                )
            ):
                new_id = str(uuid4())
                destination = diary.media.root / new_id
                destination.mkdir()
                directories.append(destination)
                for item in (diary.media.root / source.id).iterdir():
                    if item.is_file() and not item.suffix:
                        link(item, destination / item.name)
                values = {
                    key: getattr(source, key)
                    for key in (
                        "memory_date",
                        "created_at",
                        "saved_at",
                        "story",
                        "photos",
                        "track",
                        "details",
                        "title",
                        "scene",
                        "comparison",
                        "cover_style",
                        "narration",
                        "mood_tags",
                    )
                }
                db.add(Day(id=new_id, owner_id=owner, **values))
    except Exception:
        for directory in directories:
            rmtree(directory)
        raise
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=365 * 86400,
        path="/api",
    )
    return {"ready": True}
