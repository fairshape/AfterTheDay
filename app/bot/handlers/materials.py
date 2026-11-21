import asyncio
from io import BytesIO
import logging
from urllib.parse import urlsplit

from aiohttp import ClientError
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Audio, Document, Message, PhotoSize, Voice

from app.bot.copy import ERRORS, PROMPTS, STATUS
from app.bot.handlers.draft import summary
from app.bot.handlers.songs import show_results
from app.services.song_search import SongSearch
from app.bot.handlers.start import send_home
from app.infrastructure.media.storage import AUDIO_LIMIT, PHOTO_LIMIT
from app.infrastructure.db.models import Day
from app.services.diary import DETAILS, MAX_STORY, TRACK_STEPS, Diary, DraftError, missing_step
from app.services.music import URL_PATTERN, track_link
from config.settings import Settings

router = Router(name="materials")
router.message.filter(F.chat.type == ChatType.PRIVATE, F.from_user)
logger = logging.getLogger(__name__)


class AlbumReplies:
    def __init__(self):
        self.pending: dict[tuple[int, str], asyncio.Task] = {}

    def schedule(self, message: Message, day_id: str, diary: Diary, webapp_url: str = "") -> None:
        owner = message.from_user.id
        key = (owner, message.media_group_id)
        previous = self.pending.get(key)
        if previous:
            previous.cancel()

        async def reply():
            try:
                await asyncio.sleep(0.85)
                day = await asyncio.to_thread(diary.get, owner, day_id, include_draft=True)
                if day and not day.saved_at:
                    await summary(message, day, diary, webapp_url=webapp_url)
            except TelegramAPIError as exc:
                logger.warning("Could not send album summary (%s)", type(exc).__name__)
            finally:
                if self.pending.get(key) is asyncio.current_task():
                    self.pending.pop(key, None)

        self.pending[key] = asyncio.create_task(reply())

    async def close(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class LimitedBuffer(BytesIO):
    def __init__(self, limit: int, error: str):
        super().__init__()
        self.limit = limit
        self.error = error

    def write(self, data: bytes) -> int:
        if self.tell() + len(data) > self.limit:
            raise DraftError(self.error)
        return super().write(data)


def media_from(message: Message) -> tuple[str | None, Audio | Document | PhotoSize | Voice | None]:
    if message.photo:
        return "photo", message.photo[-1]
    if message.audio or message.voice:
        return "audio", message.audio or message.voice
    if message.document:
        document = message.document
        mime = document.mime_type or ""
        name = (document.file_name or "").lower()
        if mime.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return "photo", document
        if mime.startswith("audio/") or name.endswith((".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac")):
            return "audio", document
    return None, None


async def receive_file(message: Message, bot: Bot, diary: Diary, day: Day, kind: str,
                       item: Audio | Document | PhotoSize | Voice) -> str:
    if kind == "audio" and day.track and day.step not in TRACK_STEPS:
        return PROMPTS["ambiguous_track"]
    limit = PHOTO_LIMIT if kind == "photo" else AUDIO_LIMIT
    code = f"{kind}_size"
    if item.file_size and item.file_size > limit:
        raise DraftError(code)
    try:
        with LimitedBuffer(limit, code) as destination:
            await bot.download(item, destination=destination, timeout=25)
            data = destination.getvalue()
    except (TelegramAPIError, ClientError, OSError, TimeoutError) as exc:
        raise DraftError("download") from exc
    if kind == "photo":
        caption = message.caption or ""
        await asyncio.to_thread(diary.add_photo, day, data, caption, message.message_id)
        link = track_link(caption.strip())
        if link:
            return await receive_text(diary, day, link)
    else:
        title = (getattr(item, "title", None) or getattr(item, "file_name", None) or STATUS["audio_title"])[:160]
        await asyncio.to_thread(diary.set_track, day, {"kind": "file", "title": title}, data)
    return ""


async def receive_text(diary: Diary, day: Day, original: str) -> str:
    value = original.strip()
    link = track_link(value)
    if link:
        if day.track and day.step not in TRACK_STEPS:
            return PROMPTS["ambiguous_track"]
        await asyncio.to_thread(diary.set_track, day, {"kind": "link", "title": urlsplit(link).hostname, "url": link})
    elif URL_PATTERN.fullmatch(value) or value.lower().startswith(("http:", "https:", "www.")):
        raise DraftError("link")
    elif day.step in DETAILS - {"favorite"}:
        await asyncio.to_thread(diary.update_detail, day, day.step, value)
    elif not day.story or day.step == "story_edit":
        if not value or len(original) > MAX_STORY:
            raise DraftError("story_size")
        await asyncio.to_thread(diary.edit, day, story=original, step="" if day.step == "story_edit" else day.step)
    elif day.step in TRACK_STEPS or missing_step(day) == "track":
        return PROMPTS["track_name"]
    else:
        return PROMPTS["ambiguous_text"]
    return ""


@router.message()
async def material(message: Message, bot: Bot, diary: Diary, settings: Settings, albums: AlbumReplies,
                   song_search: SongSearch | None = None) -> None:
    owner = message.from_user.id
    day = await asyncio.to_thread(diary.draft, owner)
    if not day:
        await send_home(message, owner, diary, settings, PROMPTS["no_draft"])
        return
    try:
        kind, item = media_from(message)
        if kind and item:
            notice = await receive_file(message, bot, diary, day, kind, item)
            if kind == "photo" and message.media_group_id and not notice:
                albums.schedule(message, day.id, diary, settings.webapp_url)
                return
        elif message.location or message.venue:
            if day.step == "place":
                if message.venue:
                    place = message.venue.title[:120]
                else:
                    location = message.location
                    place = f"{location.latitude:.5f}, {location.longitude:.5f}"
                await asyncio.to_thread(diary.update_detail, day, "place", place)
                notice = ""
            else:
                notice = PROMPTS["location"]
        elif message.text and not message.text.startswith("/"):
            query = message.text.strip()
            if (day.step == "track_search" and song_search
                    and not query.lower().startswith(("http:", "https:", "www."))):
                await show_results(message, day, query, song_search)
                return
            notice = await receive_text(diary, day, message.text)
        else:
            notice = PROMPTS["unsupported"]
    except (DraftError, ValueError) as exc:
        notice = ERRORS.get(str(exc), ERRORS["download"])
    except OSError as exc:
        logger.error("Media storage failed (%s)", type(exc).__name__)
        notice = ERRORS["download"]
    current = await asyncio.to_thread(diary.draft, owner)
    if current:
        await summary(message, current, diary, notice, webapp_url=settings.webapp_url)
    else:
        await send_home(message, owner, diary, settings, notice or PROMPTS["no_draft"])
