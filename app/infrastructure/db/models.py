from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Index, Integer, String, Text, text
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
    scene_preview: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))


class UserPreference(Base):
    __tablename__ = "user_preferences"

    owner_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(80))
