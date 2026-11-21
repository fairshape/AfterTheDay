from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.models import FilmSource, LifeFilm
from app.services.life import assemble
from app.web.routes.diary import diary_for, owner_for

router = APIRouter(prefix="/api/films")


class Item(BaseModel):
    day: UUID
    caption: str = Field(default="", max_length=140)


class Edit(BaseModel):
    items: list[Item] = Field(min_length=2, max_length=20)
    title: str = Field(default="Мой фильм", max_length=90)
    order: Literal["date", "manual", "energy"] = "date"
    music: str = Field(default="sections", max_length=36)
    existing: UUID | None = None
    revision: int = Field(default=0, ge=0)
    seconds: int = Field(default=45, ge=12, le=180)


@router.post("/{operation}")
def build(
    operation: Literal["preview", "save"], edit: Edit, owner=Depends(owner_for), diary=Depends(diary_for)
):
    ids = [str(item.day) for item in edit.items]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "duplicate_day")
    days = [diary.get(owner, id) for id in ids]
    if not all(days):
        raise HTTPException(404, "day")
    try:
        film = assemble(days, edit)
    except ValueError as exc:
        raise HTTPException(422, "invalid_soundtrack") from exc
    if operation == "save":
        film["id"] = str(edit.existing or uuid4())
        film["editRevision"] = edit.revision + 1 if edit.existing else 1
        with diary.sessions.begin() as db:
            db.execute(text("BEGIN IMMEDIATE"))
            if edit.existing:
                saved = db.scalar(
                    select(LifeFilm).where(LifeFilm.id == film["id"], LifeFilm.owner_id == owner)
                )
                if saved is None:
                    raise HTTPException(404, "film")
                if edit.revision != saved.film.get("editRevision", 1):
                    raise HTTPException(409, "stale")
                saved.film = film
                db.execute(delete(FilmSource).where(FilmSource.film_id == film["id"]))
            else:
                db.add(
                    LifeFilm(
                        id=film["id"], owner_id=owner, created_at=datetime.now(timezone.utc), film=film
                    )
                )
            db.flush()
            db.add_all(FilmSource(day_id=day_id, film_id=film["id"]) for day_id in ids)
            try:
                db.flush()
            except IntegrityError as exc:
                raise HTTPException(409, "source_unavailable") from exc
    return film


@router.get("")
def films(owner=Depends(owner_for), diary=Depends(diary_for)):
    with diary.sessions() as db:
        rows = db.scalars(
            select(LifeFilm).where(LifeFilm.owner_id == owner).order_by(LifeFilm.created_at.desc())
        )
        return [
            {
                "id": r.id,
                "title": r.film["title"],
                "duration": r.film["duration"],
                "cover": r.film["shots"][0]["asset"],
            }
            for r in rows
        ]


@router.get("/{id}")
def get_film(id: UUID, owner=Depends(owner_for), diary=Depends(diary_for)):
    with diary.sessions() as db:
        row = db.scalar(select(LifeFilm).where(LifeFilm.id == str(id), LifeFilm.owner_id == owner))
        if not row:
            raise HTTPException(404, "film")
        return row.film


@router.post("/{id}/delete")
def delete_film(id: UUID, owner=Depends(owner_for), diary=Depends(diary_for)):
    with diary.sessions.begin() as db:
        film = db.scalar(select(LifeFilm).where(LifeFilm.id == str(id), LifeFilm.owner_id == owner))
        if film is None:
            raise HTTPException(404, "film")
        db.delete(film)
    return {"deleted": True}
