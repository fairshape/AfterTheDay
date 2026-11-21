from typing import Literal
from uuid import UUID

from sqlalchemy.dialects.sqlite import insert
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.db.models import UserPreference, Day
from app.services.anniversaries import MOODS, occurrence, reminder_settings, change_reminder
from app.web.routes.diary import diary_for, owner_for, card

router = APIRouter(prefix="/api")


class Appearance(BaseModel):
    theme: Literal["paper", "neon"]


@router.get("/appearance")
def appearance(owner=Depends(owner_for), diary=Depends(diary_for)):
    with diary.sessions() as db:
        pref = db.get(UserPreference, owner)
        return Appearance(theme=pref.theme if pref else "paper")


@router.post("/appearance")
def set_appearance(body: Appearance, owner=Depends(owner_for), diary=Depends(diary_for)):
    with diary.sessions.begin() as db:
        statement = insert(UserPreference).values(owner_id=owner, timezone=str(diary.timezone), theme=body.theme)
        db.execute(statement.on_conflict_do_update(index_elements=["owner_id"], set_={"theme": body.theme}))
    return body


class Mark(BaseModel):
    favorite: bool | None = None
    moods: list[str] | None = Field(default=None, max_length=len(MOODS))


class ReminderChange(BaseModel):
    enabled: bool
    clock: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class Preferences(BaseModel):
    auto: bool | None = None
    titles: bool | None = None
    timezone: str | None = Field(default=None, max_length=80)


@router.get("/collection")
def collection(owner=Depends(owner_for), diary=Depends(diary_for)):
    today = diary.today(owner)
    return {"worldKey": str(owner), "moods": list(MOODS), "draft": bool(diary.draft(owner)), "today": today.isoformat(),
            "anniversaries": [card(day) for day in diary.archive(owner) if day.memory_date.year < today.year
                              and occurrence(day.memory_date, today.year) == today]}


@router.post("/days/{day_id}/marks")
def marks(day_id: UUID, body: Mark, owner=Depends(owner_for), diary=Depends(diary_for)):
    if body.moods is not None and set(body.moods) - MOODS.keys():
        raise HTTPException(422, "moods")
    with diary.sessions.begin() as db:
        day = db.get(Day, str(day_id))
        if not day or day.owner_id != owner or not day.saved_at:
            raise HTTPException(404, "day")
        if body.favorite is not None:
            day.favorite = body.favorite
        if body.moods is not None:
            day.mood_tags = list(dict.fromkeys(body.moods))
        return card(day)


@router.get("/reminders")
def reminders(owner=Depends(owner_for), diary=Depends(diary_for)):
    return reminder_settings(diary, owner)


@router.post("/reminders/settings")
def settings(body: Preferences, owner=Depends(owner_for), diary=Depends(diary_for)):
    if body.timezone is not None:
        try:
            ZoneInfo(body.timezone)
        except (ValueError, ZoneInfoNotFoundError):
            raise HTTPException(422, "timezone")
    with diary.sessions.begin() as db:
        pref = db.get(UserPreference, owner) or UserPreference(owner_id=owner, timezone=str(diary.timezone))
        for field, attr in (("auto","auto_anniversary"), ("titles","show_title"), ("timezone","timezone")):
            value = getattr(body, field)
            if value is not None:
                setattr(pref, attr, value)
        db.add(pref)
    return reminder_settings(diary, owner)


@router.post("/reminders/{day_id}")
def reminder(day_id: UUID, body: ReminderChange, owner=Depends(owner_for), diary=Depends(diary_for)):
    try:
        change_reminder(diary, owner, str(day_id), body.enabled, body.clock)
    except LookupError:
        raise HTTPException(404, "day")
    return reminder_settings(diary, owner)
