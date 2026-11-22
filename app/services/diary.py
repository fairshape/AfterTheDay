from datetime import date, datetime, timedelta, timezone
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.infrastructure.audio.analysis import analyze_audio
from app.infrastructure.db.models import Day, UserPreference
from app.infrastructure.media.storage import MediaStore
from app.services.anniversaries import MOODS, new_publication, tags
from app.services.context import date_search, visible_place
from app.services.art_direction import COLORS, STICKERS
from app.services.narration import Narration, assets_for
from app.services.music import PROFILES, track_link
from app.services.scene import build_scene

MAX_PHOTOS = 10
MAX_STORY = 12_000
DEMO_OWNER = 0
TRACK_STEPS = {"track_edit", "track_search", "track_link", "track_file"}
DETAILS = {"date", "time", "place", "place_label", "weather", "mood", "key_detail", "favorite", "cue"}


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
    def __init__(self, sessions, media: MediaStore, timezone_name: str, voice: Narration | None = None):
        self.sessions = sessions
        self.media = media
        self.voice = voice
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
            local_date = self.today(owner)
            day = Day(id=str(uuid4()), owner_id=owner, created_at=datetime.now(timezone.utc),
                      memory_date=local_date, details={"_creation_date": local_date.isoformat()})
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
        labels = set(re.split(r"[,\s+]+", needle)) - {"", "и"}
        if labels and labels <= MOODS.keys():
            return [day for day in days if labels <= set(tags(day))]
        return [day for day in days if any(needle in field.casefold()
                for field in (day.title, day.story, visible_place(day.details), *date_search(day.memory_date)))] if needle else days

    def get(self, owner: int, day_id: str, *, include_draft: bool = False) -> Day | None:
        with self.sessions() as session:
            statement = select(Day).where(Day.owner_id == owner, Day.id == day_id)
            if not include_draft:
                statement = statement.where(Day.saved_at.is_not(None))
            return session.scalar(statement)

    def edit(self, day: Day, **changes) -> Day:
        if day.story != changes.get("story", day.story):
            changes.update(narration={}, voice_preview={})
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day.id, Day.owner_id == day.owner_id,
                       Day.saved_at.is_(None), Day.revision == day.revision)
                       .values(**changes, revision=day.revision + 1))
            if result.rowcount != 1:
                raise DraftError("stale")
            if changes.get("saved_at"):
                new_publication(session, day)
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
                if not value:
                    fallback = details.get("_creation_date")
                    if fallback:
                        memory_date = date.fromisoformat(fallback)
                    else:
                        with self.sessions() as session:
                            preference = session.get(UserPreference, day.owner_id)
                        local_zone = ZoneInfo(preference.timezone) if preference else self.timezone
                        memory_date = day.created_at.replace(tzinfo=timezone.utc).astimezone(local_zone).date()
                    details["event_date"] = None
                elif value.casefold() in {"today", "сегодня"}:
                    memory_date = self.today(day.owner_id)
                elif value.casefold() in {"yesterday", "вчера"}:
                    memory_date = self.today(day.owner_id) - timedelta(days=1)
                elif re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
                    dd, mm, yyyy = value.split(".")
                    memory_date = date.fromisoformat(f"{yyyy}-{mm}-{dd}")
                else:
                    memory_date = date.fromisoformat(value)
                if value:
                    details["event_date"] = memory_date.isoformat()
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
            key = {"favorite": "favorite_photo", "place_label": "place"}.get(key, key)
            if not value:
                details.pop(key, None)
                if key == "place":
                    details.pop("coordinates", None)
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
        try:
            return self.edit(day, photos=photos)
        except Exception:
            self.media.remove(day.id, asset["id"])
            raise

    def accept_photo_caption(self, day: Day, asset_id: str) -> Day:
        caption = next((photo["caption"] for photo in day.photos if photo["id"] == asset_id), "")
        if day.story or not caption.strip() or track_link(caption.strip()):
            raise DraftError("stale")
        return self.edit(day, story=caption, step="")

    def share_location(self, day: Day, latitude: float, longitude: float, label: str = "") -> Day:
        if day.step != "place" or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise DraftError("detail")
        details = {**day.details, "coordinates": {"latitude": round(latitude, 5), "longitude": round(longitude, 5)}}
        if label:
            details["place"] = label[:120]
        else:
            details.pop("place", None)
        return self.edit(day, details=details, step="" if label else "place_label")

    def remove_photo(self, day: Day, asset_id: str) -> Day:
        if not any(photo["id"] == asset_id for photo in day.photos):
            raise DraftError("stale")
        details = dict(day.details)
        if details.get("cover_photo") == asset_id:
            details.pop("cover_photo")
        if details.get("favorite_photo") == asset_id:
            details.pop("favorite_photo")
        self.edit(day, photos=[photo for photo in day.photos if photo["id"] != asset_id], details=details,
                  cover_style={} if day.cover_style.get("photo") == asset_id else day.cover_style)
        self.media.remove(day.id, asset_id)
        return day

    def set_track(self, day: Day, track: dict, data: bytes | None = None) -> Day:
        old_asset = day.track.get("id")
        if data is not None:
            track = {**track, **self.media.ingest(day.id, data, "audio")}
            if "profile" not in track:
                analysis = analyze_audio(self.media.path(day.id, track["id"]), track["mime"])
                if analysis and analysis.tempo and analysis.confidence >= .5:
                    track.update(profile="rhythmic" if analysis.tempo >= 105 else "calm", signal="waveform")
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
        for asset in [*day.photos, day.track, *assets_for(day)]:
            if asset.get("id"):
                self.media.remove(day.id, asset["id"])

    def paper_layout(self, day: Day, scene: dict) -> None:
        family = scene["emotion"]["family"]
        saved = day.scene.get("emotion", {})
        if saved.get("family") == family and "layout" in saved:
            scene["emotion"]["layout"] = saved["layout"]
            return
        with self.sessions() as db:
            recent = db.scalars(select(Day.scene).where(
                Day.owner_id == day.owner_id, Day.saved_at.is_not(None), Day.id != day.id
            ).order_by(Day.saved_at.desc()).limit(4))
            # The photo's proportions break ties. Switch composition when recent
            # pages already use the same visual and rhythmic vocabulary.
            preferred = "spread" if scene["palette"].get("mainAspect", 1) > 1.4 else "portrait"
            costs = {"spread": 0., "portrait": 0.}
            for previous in recent:
                art = previous.get("emotion", {})
                layout = art.get("layout")
                if layout not in costs:
                    continue
                palette = previous.get("palette", {})
                signals = previous.get("signals", {})
                similarity = sum((
                    art.get("family") == family,
                    art.get("type") == scene["emotion"]["type"],
                    abs(palette.get("mainLight", .5) - scene["palette"].get("mainLight", .5)) < .14,
                    abs(art.get("warmth", .5) - scene["emotion"]["warmth"]) < .12,
                    abs(previous.get("grain", 0) - scene["grain"]) < .025,
                    abs(signals.get("transition", 0) - scene["signals"]["transition"]) < .18,
                    abs(signals.get("baseSeconds", 0) - scene["signals"]["baseSeconds"]) < .8,
                ))
                if similarity >= 4:
                    costs[layout] += similarity
        scene["emotion"]["layout"] = min(costs, key=lambda layout: (costs[layout], layout != preferred))

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
        scene = build_scene(self.media, day.id, day.story, day.photos, day.track, day.details, moods=day.mood_tags,
                            even_comparison=owner == DEMO_OWNER and bool(comparison))
        self.paper_layout(day, scene)
        alternate = build_scene(self.media, day.id, day.story, day.photos, comparison,
                                day.details, base=scene, moods=day.mood_tags, match_cut=True) if comparison else {}
        spoken = day.narration
        if spoken and self.voice:
            spoken = self.voice.build(day, scene, spoken["voice"], spoken["rate"], spoken)
        try:
            return self.edit(day, title=scene["title"], narration=spoken, scene=scene, comparison=alternate,
                             step="", scene_preview={}, saved_at=datetime.now(timezone.utc))
        except DraftError:
            existing = self.get(owner, day_id)
            if existing is not None:
                return existing
            raise

    def set_cover(self, owner: int, day_id: str, style: dict, moods: list[str] | None = None,
                  *, choices: dict | None = None, voice: dict | None = None, revision: int | None = None,
                  preview_token: str | None = None) -> Day:
        day = self.get(owner, day_id, include_draft=True)
        if not day or (not day.saved_at and day.scene_preview.get("revision") != day.revision):
            raise DraftError("missing_day")
        scene = day.scene if day.saved_at else day.scene_preview["scene"]
        if moods is not None and set(moods) - MOODS.keys():
            raise DraftError("invalid_cover")
        if style and ((style["color"] == "auto" and not scene.get("palette", {}).get("field"))
                      or style["color"] not in {*COLORS, "auto"} or style["sticker"] not in {*STICKERS, "none"}
                      or not any(photo["id"] == style["photo"] for photo in day.photos)):
            raise DraftError("invalid_cover")
        conditions = [Day.id == day_id, Day.owner_id == owner, Day.revision == day.revision]
        changes = {"cover_style": style}
        if moods is not None:
            changes["mood_tags"] = list(dict.fromkeys(moods))
        if revision is not None:
            if day.revision != revision:
                raise DraftError("stale")
            changes["revision"] = revision + 1
            changes["voice_preview"] = {}
            pending = day.scene_preview if not day.saved_at else {}
            if pending:
                if pending.get("token") != preview_token:
                    raise DraftError("stale")
                conditions.append(Day.scene_preview["token"].as_string() == preview_token)
            if choices:
                candidate = self.assemble_candidate(day, choices, voice)
            else:
                candidate = {**pending, "scene": scene, "narration": pending.get("narration", day.narration)}
                if voice:
                    if not self.voice:
                        raise DraftError("speech_unavailable")
                    candidate["narration"] = self.voice.build(day, scene, voice["voice"], voice["rate"], candidate["narration"])
            changes["narration"] = candidate["narration"]
            if pending:
                changes["scene_preview"] = {**candidate, "revision": revision + 1, "token": uuid4().hex}
            else:
                changes["scene_preview"] = {}
                if choices:
                    changes.update(scene=candidate["scene"], details=candidate["details"], comparison=candidate["comparison"])
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(*conditions).values(**changes))
            if result.rowcount != 1:
                raise DraftError("stale")
        return self.get(owner, day_id, include_draft=True)

    def first_saved_id(self, owner: int) -> str | None:
        with self.sessions() as session:
            return session.scalar(select(Day.id).where(Day.owner_id == owner, Day.saved_at.is_not(None))
                                  .order_by(Day.saved_at, Day.id).limit(1))

    def assemble_candidate(self, day: Day, choices: dict, voice: dict | None = None) -> dict:
        pending = day.scene_preview if not day.saved_at and day.scene_preview.get("revision") == day.revision else {}
        details = dict(pending.get("details", day.details))
        track = dict(pending.get("track", day.track))
        if "alternate_track" in choices:
            if not day.saved_at or day.revision != choices["revision"]:
                raise DraftError("stale")
            photo_ids = {photo["id"] for photo in day.photos}
            reference_ids = {frame.get("asset") for frame in day.scene["frames"]}
            if not reference_ids or not reference_ids <= photo_ids or any(
                not self.media.path(day.id, asset_id).is_file() for asset_id in reference_ids
            ):
                raise DraftError("asset_unavailable")
            alternate = build_scene(
                self.media, day.id, day.story, day.photos, choices["alternate_track"],
                details, moods=day.mood_tags, base=day.scene, match_cut=True,
            )
            return {"token": uuid4().hex, "revision": day.revision, "scene": day.scene,
                    "comparison": alternate, "details": details, "track": track, "narration": day.narration}
        if "studio" in choices:
            studio = choices["studio"] or {}
            order = studio.get("order", [])
            photo_ids = {photo["id"] for photo in day.photos}
            if order and (set(order) != photo_ids or len(order) != len(photo_ids)):
                raise DraftError("invalid_pin")
            details["studio"] = studio
        if choices.get("resetCaptions"):
            details.pop("_captions", None)
        if "captions" in choices:
            captions = choices["captions"]
            photos = {photo["id"] for photo in day.photos}
            if any(key.split(":")[0] not in photos for key in captions):
                raise DraftError("invalid_pin")
            details["_captions"] = {**details.get("_captions", {}), **captions}
        if "replacement" in choices:
            if day.revision != choices["revision"]:
                raise DraftError("stale")
            if track.get("id"):
                # Saved films can still reference the previous cut's music.
                previous = {item["id"]: item for item in details.get("_previous_audio", [])}
                previous[track["id"]] = track
                details["_previous_audio"] = list(previous.values())
            track = choices["replacement"]
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

        scene = build_scene(self.media, day.id, day.story, day.photos, track, details, moods=day.mood_tags, base=day.scene or None,
                            even_comparison=day.owner_id == DEMO_OWNER and bool(day.comparison))
        self.paper_layout(day, scene)
        comparison = (build_scene(self.media, day.id, day.story, day.photos, day.comparison["track"],
                                  details, moods=day.mood_tags, base=scene, match_cut=True) if day.comparison else {})
        spoken = pending.get("narration", day.narration)
        if voice or spoken:
            if not self.voice:
                raise DraftError("speech_unavailable")
            selected = voice or spoken
            spoken = self.voice.build(day, scene, selected["voice"], selected["rate"], spoken)
        return {"token": uuid4().hex, "revision": day.revision, "scene": scene, "comparison": comparison,
                     "details": details, "track": track, "narration": spoken}

    def preview_scene(self, owner: int, day_id: str, choices: dict) -> tuple[Day, dict]:
        day = self.get(owner, day_id, include_draft=True)
        if not day:
            raise DraftError("missing_day")
        if missing_step(day):
            raise DraftError("incomplete")
        if not choices and not day.saved_at and day.scene_preview.get("revision") == day.revision:
            return day, day.scene_preview
        candidate = self.assemble_candidate(day, choices)
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day_id, Day.owner_id == owner,
                         Day.revision == day.revision).values(scene_preview=candidate))
            if result.rowcount != 1:
                raise DraftError("stale")
        if self.voice:
            day.scene_preview = candidate
            self.voice.prune(day)
        return day, candidate

    def commit_preview(self, owner: int, day_id: str, token: str) -> tuple[Day, bool]:
        day = self.get(owner, day_id, include_draft=True)
        if not day:
            raise DraftError("missing_day")
        pending = day.scene_preview
        if day.saved_at and pending.get("publishedToken") == token:
            return day, False
        if pending.get("token") != token or pending.get("revision") != day.revision:
            raise DraftError("stale")
        with self.sessions.begin() as session:
            result = session.execute(update(Day).where(Day.id == day_id, Day.owner_id == owner,
                         Day.revision == day.revision, Day.scene_preview["token"].as_string() == token)
                         .values(scene=pending["scene"], comparison=pending["comparison"], scene_preview={"publishedToken": token},
                                 details=pending["details"], track=pending["track"], title=pending["scene"]["title"],
                                 narration=pending.get("narration", day.narration), voice_preview={},
                                 saved_at=day.saved_at or datetime.now(timezone.utc), step="", revision=day.revision+1))
            if result.rowcount == 1 and not day.saved_at:
                new_publication(session, day)
        saved = self.get(owner, day_id)
        if result.rowcount != 1:
            if saved and saved.scene_preview.get("publishedToken") == token:
                return saved, False
            raise DraftError("stale")
        return saved, day.saved_at is None

    def pin(self, owner: int, day_id: str, photo_id: str | None, quote: str | None) -> Day:
        if self.get(owner, day_id) is None:
            raise DraftError("stale")
        choices = {}
        if photo_id is not None:
            choices["photo"] = photo_id
        if quote is not None:
            choices["quote"] = quote
        _, candidate = self.preview_scene(owner, day_id, choices)
        saved, _ = self.commit_preview(owner, day_id, candidate["token"])
        return saved
