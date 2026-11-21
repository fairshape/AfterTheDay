from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Day(Base):
    __tablename__ = "days"
    __table_args__ = (
        Index("ix_days_owner_draft", "owner_id", unique=True, sqlite_where=text("saved_at IS NULL")),
        Index("ix_days_archive", "owner_id", "memory_date", "saved_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    memory_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[str] = mapped_column(String(24), default="")
    story: Mapped[str] = mapped_column(Text, default="")
    photos: Mapped[list] = mapped_column(JSON, default=list)
    track: Mapped[dict] = mapped_column(JSON, default=dict)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    title: Mapped[str] = mapped_column(Text, default="")
    scene: Mapped[dict] = mapped_column(JSON, default=dict)
    comparison: Mapped[dict] = mapped_column(JSON, default=dict)
    cover_style: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    favorite: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    mood_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scene_preview: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    narration: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    voice_preview: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))


class UserPreference(Base):
    __tablename__ = "user_preferences"

    owner_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    auto_anniversary: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    show_title: Mapped[bool] = mapped_column(default=False, server_default=text("0"))
    timezone: Mapped[str] = mapped_column(String(80))


class Anniversary(Base):
    __tablename__ = "anniversaries"
    day_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    clock: Mapped[str] = mapped_column(String(5))


class Delivery(Base):
    __tablename__ = "anniversary_deliveries"
    day_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16))


class LifeFilm(Base):
    __tablename__ = "life_films"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    film: Mapped[dict] = mapped_column(JSON)


class FilmSource(Base):
    __tablename__ = "film_sources"
    film_id: Mapped[str] = mapped_column(ForeignKey("life_films.id", ondelete="CASCADE"), primary_key=True)
    day_id: Mapped[str] = mapped_column(ForeignKey("days.id", ondelete="RESTRICT"), primary_key=True, index=True)
