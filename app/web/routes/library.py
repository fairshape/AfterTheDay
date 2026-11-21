"""Operations on the published memory and its source folder."""

from datetime import date
from shutil import rmtree
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.models import Anniversary, Day, Delivery, UserPreference
from app.services.anniversaries import schedule
from app.web.routes.diary import diary_for, owner_for

router = APIRouter(prefix="/api/days")


class Version(BaseModel):
    revision: int = Field(ge=0)


class Metadata(Version):
    title: str = Field(min_length=1, max_length=90)
    date: date
    reflection: str = Field(max_length=360)


@router.post("/{day_id}/metadata")
def metadata(day_id: UUID, body: Metadata, owner=Depends(owner_for), diary=Depends(diary_for)):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
    title = body.title.strip()
    if not title:
        raise HTTPException(422, "title")
    details = {**day.details, "custom_title": title, "reflection": body.reflection.strip()}
    if body.date != day.memory_date:
        details["event_date"] = body.date.isoformat()
    with diary.sessions.begin() as db:
        result = db.execute(
            update(Day)
            .where(Day.id == day.id, Day.owner_id == owner, Day.revision == body.revision)
            .values(
                title=title,
                details=details,
                memory_date=body.date,
                scene={**day.scene, "title": title},
                comparison={**day.comparison, "title": title} if day.comparison else {},
                revision=day.revision + 1,
                scene_preview={},
            )
        )
        if result.rowcount != 1:
            raise HTTPException(409, "stale")
        reminder = db.get(Anniversary, day.id)
        if reminder and body.date != day.memory_date:
            pref = db.get(UserPreference, owner)
            clock = reminder.clock
            db.delete(reminder)
            db.flush()
            schedule(db, db.get(Day, day.id), pref.timezone if pref else str(diary.timezone), clock)
    return {"saved": True}


@router.post("/{day_id}/delete")
def delete_day(day_id: UUID, body: Version, owner=Depends(owner_for), diary=Depends(diary_for)):
    day = diary.get(owner, str(day_id))
    if day is None:
        raise HTTPException(404, "day")
    try:
        with diary.sessions.begin() as db:
            result = db.execute(
                delete(Day).where(Day.id == day.id, Day.owner_id == owner, Day.revision == body.revision)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "stale")
            db.execute(delete(Anniversary).where(Anniversary.day_id == day.id))
            db.execute(delete(Delivery).where(Delivery.day_id == day.id))
    except IntegrityError as exc:
        raise HTTPException(409, "film_uses_day") from exc
    directory = diary.media.root / str(day_id)
    if directory.exists():
        rmtree(directory)
    return {"deleted": True}
