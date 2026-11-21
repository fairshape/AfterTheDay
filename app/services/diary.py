from datetime import date, datetime, timedelta, timezone
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.models import Day, UserPreference
from app.infrastructure.media.storage import MediaStore
from app.services.art_direction import COLORS, STICKERS
from app.services.music import PROFILES, track_link
from app.services.scene import build_scene

MAX_PHOTOS = 10
MAX_STORY = 12_000
DEMO_OWNER = 0
TRACK_STEPS = {"track_edit", "track_search", "track_link", "track_file"}
DETAILS = {"date", "time", "place", "weather", "mood", "key_detail", "favorite", "cue"}


class DraftError(ValueError):
    pass


def missing_step(day: Day) -> str:
    if not day.story.strip():
        return "story"
    if not day.photos:
        return "photo"
    if not day.track:
        return "track"
    if day.track.get("profile") not in PROFILES:
        return "profile"
    return ""


class Diary:
    def __init__(self, sessions, media: MediaStore, timezone_name: str):
        self.sessions = sessions
        self.media = media
        self.timezone = ZoneInfo(timezone_name)

    def today(self, owner: int) -> date:
        with self.sessions() as session:
            preference = session.get(UserPreference, owner)
        timezone_for_user = ZoneInfo(preference.timezone) if preference else self.timezone
        return datetime.now(timezone_for_user).date()

    def set_timezone(self, owner: int, name: str) -> None:
        try:
            if not 1 <= len(name) <= 80:
                raise ValueError
            ZoneInfo(name)
        except (KeyError, ValueError) as exc:
            raise DraftError("timezone") from exc
        with self.sessions.begin() as session:
            session.merge(UserPreference(owner_id=owner, timezone=name))

    def draft(self, owner: int, *, create: bool = False) -> Day | None:
        statement = select(Day).where(Day.owner_id == owner, Day.saved_at.is_(None))
        with self.sessions() as session:
            day = session.scalar(statement)
            if day or not create:
                return day
            day = Day(id=str(uuid4()), owner_id=owner, created_at=datetime.now(timezone.utc),
                      memory_date=self.today(owner))
            session.add(day)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return session.scalars(statement).one()
            return day

    def archive(self, owner: int, query: str = "") -> list[Day]:
        statement = (select(Day).where(Day.owner_id == owner, Day.saved_at.is_not(None))
                     .order_by(Day.memory_date.desc(), Day.saved_at.desc()))
        with self.sessions() as session:
            days = list(session.scalars(statement))
        needle = query.casefold().strip()
        return [day for day in days if any(needle in field.casefold()
                for field in (day.title, day.story, day.details.get("place", "")))] if needle else days

    def get(self, owner: int, day_id: str, *, include_draft: bool = False) -> Day | None:
        with self.sessions() as session:
            statement = select(Day).where(Day.owner_id == owner, Day.id == day_id)
            if not include_draft:
                statement = statement.where(Day.saved_at.is_not(None))
            return session.scalar(statement)

    def edit(self, day: Day, **changes) -> Day:
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day.id, Day.owner_id == day.owner_id,
                       Day.saved_at.is_(None), Day.revision == day.revision)
                       .values(**changes, revision=day.revision + 1))
            if result.rowcount != 1:
                raise DraftError("stale")
        for key, value in changes.items():
            setattr(day, key, value)
        day.revision += 1
        return day

    def update_detail(self, day: Day, key: str, raw: str | None = None) -> None:
        details = dict(day.details)
        track = dict(day.track)
        memory_date = day.memory_date
        value = raw.strip() if raw else ""
        if key == "date":
            try:
                if not value or value.casefold() in {"today", "сегодня"}:
                    memory_date = self.today(day.owner_id)
                elif value.casefold() in {"yesterday", "вчера"}:
                    memory_date = self.today(day.owner_id) - timedelta(days=1)
                elif re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
                    dd, mm, yyyy = value.split(".")
                    memory_date = date.fromisoformat(f"{yyyy}-{mm}-{dd}")
                else:
                    memory_date = date.fromisoformat(value)
            except ValueError as exc:
                raise DraftError("date") from exc
        elif key == "cue":
            if track.get("kind") != "file":
                raise DraftError("cue_link")
            if not value:
                track.pop("cue", None)
            else:
                match = re.fullmatch(r"(?:(\d{1,3}):([0-5]\d)|(\d{1,5}))", value)
                if not match:
                    raise DraftError("cue")
                cue = int(match[3]) if match[3] else int(match[1]) * 60 + int(match[2])
                if not 0 <= cue < track["duration"]:
                    raise DraftError("cue")
                track["cue"] = cue
        else:
            key = "favorite_photo" if key == "favorite" else key
            if not value:
                details.pop(key, None)
            else:
                if key == "time":
                    if not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", value):
                        if ":" in value or not any(character.isalpha() for character in value) or len(value) > 40:
                            raise DraftError("time")
                if len(value) > (108 if key == "key_detail" else 120):
                    raise DraftError("detail")
                details[key] = value
        self.edit(day, details=details, track=track, memory_date=memory_date, step="")


    def add_photo(self, day: Day, data: bytes, caption: str, message_id: int | None = None) -> Day:
        if message_id is not None and any(photo.get("message_id") == message_id for photo in day.photos):
            return day
        if len(day.photos) >= MAX_PHOTOS:
            raise DraftError("photo_limit")
        asset = self.media.ingest(day.id, data, "photo")
        photo = {**asset, "caption": caption, "message_id": message_id}
        photos = [*day.photos, photo]
        if message_id is not None:
            photos.sort(key=lambda item: item.get("message_id") or 0)
        changes = {"photos": photos}
        if caption.strip() and not day.story and not track_link(caption.strip()):
            changes["story"] = caption
        try:
            return self.edit(day, **changes)
        except Exception:
            self.media.remove(day.id, asset["id"])
            raise

    def remove_photo(self, day: Day, asset_id: str) -> Day:
        if not any(photo["id"] == asset_id for photo in day.photos):
            raise DraftError("stale")
        details = dict(day.details)
        if details.get("favorite_photo") == asset_id:
            details.pop("favorite_photo")
        self.edit(day, photos=[photo for photo in day.photos if photo["id"] != asset_id], details=details)
        self.media.remove(day.id, asset_id)
        return day

    def set_track(self, day: Day, track: dict, data: bytes | None = None) -> Day:
        old_asset = day.track.get("id")
        if data is not None:
            track = {**track, **self.media.ingest(day.id, data, "audio")}
        asset_id = track.get("id")
        try:
            self.edit(day, track=track, step="" if day.step in TRACK_STEPS | {"profile", "cue"} else day.step)
        except Exception:
            if asset_id:
                self.media.remove(day.id, asset_id)
            raise
        if old_asset:
            self.media.remove(day.id, old_asset)
        return day

    def cancel(self, day: Day) -> None:
        with self.sessions.begin() as session:
            result = session.execute(Day.__table__.delete().where(
                Day.id == day.id, Day.owner_id == day.owner_id,
                Day.saved_at.is_(None), Day.revision == day.revision))
            if result.rowcount != 1:
                raise DraftError("stale")
        for asset in [*day.photos, day.track]:
            if asset.get("id"):
                self.media.remove(day.id, asset["id"])

    def save(self, owner: int, day_id: str, *, comparison: dict | None = None) -> Day:
        day = self.get(owner, day_id, include_draft=True)
        if not day:
            raise DraftError("stale")
        if day.saved_at:
            return day
        if missing_step(day):
            raise DraftError("incomplete")

        referenced = [*day.photos, day.track, comparison or {}]
        if any(asset.get("id") and not self.media.path(day.id, asset["id"]).is_file() for asset in referenced):
            raise DraftError("asset_missing")

        # Generation completes before publishing. A revision check prevents publishing inputs
        # that changed while building, and the draft ID becomes the permanent day ID.
        scene = build_scene(self.media, day.id, day.story, day.photos, day.track, day.details,
                            even_comparison=owner == DEMO_OWNER and bool(comparison))
        alternate = build_scene(self.media, day.id, day.story, day.photos, comparison,
                                day.details, base=scene) if comparison else {}
        try:
            return self.edit(day, title=scene["title"], scene=scene, comparison=alternate,
                             step="", scene_preview={}, saved_at=datetime.now(timezone.utc))
        except DraftError:
            existing = self.get(owner, day_id)
            if existing is not None:
                return existing
            raise

    def set_cover(self, owner: int, day_id: str, style: dict) -> Day:
        day = self.get(owner, day_id)
        if not day:
            raise DraftError("missing_day")
        if style and ((style["color"] == "auto" and not day.scene.get("palette", {}).get("field"))
                      or style["color"] not in {*COLORS, "auto"} or style["sticker"] not in STICKERS
                      or not any(photo["id"] == style["photo"] for photo in day.photos)):
            raise DraftError("invalid_cover")
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day_id, Day.owner_id == owner,
                         Day.saved_at.is_not(None), Day.revision == day.revision)
                         .values(cover_style=style, revision=day.revision + 1))
            if result.rowcount != 1:
                raise DraftError("stale")
        return self.get(owner, day_id)

    def first_saved_id(self, owner: int) -> str | None:
        with self.sessions() as session:
            return session.scalar(select(Day.id).where(Day.owner_id == owner, Day.saved_at.is_not(None))
                                  .order_by(Day.saved_at, Day.id).limit(1))

    def preview_scene(self, owner: int, day_id: str, choices: dict) -> tuple[Day, dict]:
        day = self.get(owner, day_id, include_draft=True)
        if not day:
            raise DraftError("missing_day")
        if missing_step(day):
            raise DraftError("incomplete")
        details = dict(day.details)
        track = dict(day.track)
        if "photo" in choices:
            photo_id = choices["photo"]
            if photo_id and not any(photo["id"] == photo_id for photo in day.photos):
                raise DraftError("invalid_pin")
            details["favorite_photo"] = photo_id or ""
        if "cue" in choices:
            if track["kind"] != "file":
                raise DraftError("cue_link")
            cue = choices["cue"]
            if cue is None:
                track.pop("cue", None)
            elif 0 <= cue < track["duration"]:
                track["cue"] = cue
            else:
                raise DraftError("cue")
        if "quote" in choices:
            quote = choices["quote"] or ""
            if quote and " ".join(quote.casefold().split()) not in " ".join(day.story.casefold().split()):
                raise DraftError("invalid_pin")
            details["key_detail"] = quote

        scene = build_scene(self.media, day.id, day.story, day.photos, track, details, base=day.scene or None,
                            even_comparison=owner == DEMO_OWNER and bool(day.comparison))
        comparison = (build_scene(self.media, day.id, day.story, day.photos, day.comparison["track"],
                                  details, base=scene) if day.comparison else {})
        candidate = {"token": uuid4().hex, "revision": day.revision, "scene": scene, "comparison": comparison,
                     "details": details, "track": track}
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day_id, Day.owner_id == owner,
                         Day.revision == day.revision).values(scene_preview=candidate))
            if result.rowcount != 1:
                raise DraftError("stale")
        return day, candidate

    def commit_preview(self, owner: int, day_id: str, token: str) -> Day:
        day = self.get(owner, day_id, include_draft=True)
        if not day:
            raise DraftError("missing_day")
        pending = day.scene_preview
        if pending.get("token") != token or pending.get("revision") != day.revision:
            raise DraftError("stale")
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day_id, Day.owner_id == owner,
                         Day.revision == day.revision, Day.scene_preview["token"].as_string() == token)
                         .values(scene=pending["scene"], comparison=pending["comparison"], scene_preview={},
                                 details=pending["details"], track=pending["track"], title=pending["scene"]["title"],
                                 saved_at=day.saved_at or datetime.now(timezone.utc), step="", revision=day.revision+1))
            if result.rowcount != 1:
                raise DraftError("stale")
        return self.get(owner, day_id)

    def pin(self, owner: int, day_id: str, photo_id: str | None, quote: str | None) -> Day:
        if self.get(owner, day_id) is None:
            raise DraftError("stale")
        choices = {}
        if photo_id is not None:
            choices["photo"] = photo_id
        if quote is not None:
            choices["quote"] = quote
        _, candidate = self.preview_scene(owner, day_id, choices)
        return self.commit_preview(owner, day_id, candidate["token"])
