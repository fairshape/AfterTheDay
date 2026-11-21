import asyncio
from html import escape
import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.copy import ERRORS, LABELS, MOODS, PROMPTS
from app.bot.handlers.start import send_home
from app.bot.keyboards import action, keyboard, web_link
from app.bot.messages import reply, send_optional_sticker
from app.bot.summaries import show_draft
from app.infrastructure.db.models import Day
from app.services.diary import DETAILS, Diary, DraftError
from app.services.music import PROFILES
from config.settings import Settings

if TYPE_CHECKING:
    from app.bot.handlers.materials import AlbumReplies

router = Router(name="draft")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
logger = logging.getLogger(__name__)
EDIT_MODES = {"story_edit", "photo_edit", "track_edit", "profile"}


async def summary(message: Message, day: Day, diary: Diary, notice: str = "", *, replace: bool = False) -> None:
    await show_draft(message, day, notice, timezone_year=(await asyncio.to_thread(diary.today, day.owner_id)).year,
                     replace=replace)


@router.message(Command("cancel"))
async def cancel_command(message: Message, diary: Diary, settings: Settings) -> None:
    day = await asyncio.to_thread(diary.draft, message.from_user.id)
    if day:
        await reply(message, PROMPTS["cancel"], keyboard(
            (action("yes_delete", f"delete:{day.id}"), action("back", "draft:back")),
        ))
    else:
        await send_home(message, message.from_user.id, diary, settings, PROMPTS["no_draft"])


@router.callback_query(F.data.startswith(("draft:", "step:", "profile:", "date:", "mood:", "favorite:", "remove:", "clear:", "delete:")))
async def draft_action(callback: CallbackQuery, diary: Diary, settings: Settings) -> None:
    await callback.answer()
    operation, value = callback.data.split(":", 1)
    owner = callback.from_user.id
    message = callback.message
    day = await asyncio.to_thread(diary.draft, owner, create=(operation, value) == ("draft", "new"))
    if not day:
        await send_home(message, owner, diary, settings, PROMPTS["no_draft"])
        return
    try:
        if (operation, value) == ("draft", "details"):
            buttons = lambda *keys: tuple(action(key, f"step:{key}") for key in keys)
            await reply(message, PROMPTS["details"], keyboard(
                buttons("date", "time", "place"), buttons("weather", "mood"), buttons("key_detail", "favorite"),
                buttons("cue") if day.track.get("kind") == "file" else (), (action("back", "draft:back"),),
            ), replace=True)
            return
        if (operation, value) == ("draft", "edit"):
            await reply(message, PROMPTS["edit"], keyboard(
                (action("story", "step:story_edit"), action("photo", "step:photo_edit"), action("track", "step:track_edit")),
                (action("profile", "step:profile"),) if day.track else (), (action("back", "draft:back"),),
            ), replace=True)
            return
        if (operation, value) == ("draft", "cancel"):
            await reply(message, PROMPTS["cancel"], keyboard(
                (action("yes_delete", f"delete:{day.id}"), action("back", "draft:back")),
            ), replace=True)
            return
        if operation == "delete":
            if day.id != value:
                raise DraftError("stale")
            await asyncio.to_thread(diary.cancel, day)
            await send_home(message, owner, diary, settings, PROMPTS["cancelled"])
            return
        if operation == "draft" and value == "back":
            await asyncio.to_thread(diary.edit, day, step="")
        elif operation == "step" and value in DETAILS | EDIT_MODES:
            if value == "cue" and day.track.get("kind") != "file":
                raise DraftError("cue_link")
            if value == "profile" and not day.track:
                raise DraftError("stale")
            await asyncio.to_thread(diary.edit, day, step=value)
        elif operation == "profile" and value in PROFILES and day.track:
            await asyncio.to_thread(diary.edit, day, track={**day.track, "profile": value, "signal": "user"}, step="")
        elif operation == "date" and value in {"today", "yesterday"}:
            await asyncio.to_thread(diary.update_detail, day, "date", value)
        elif operation == "mood" and value in MOODS:
            await asyncio.to_thread(diary.update_detail, day, "mood", MOODS[value])
        elif operation == "clear" and value in DETAILS:
            await asyncio.to_thread(diary.update_detail, day, value)
        elif operation == "favorite" and any(photo["id"] == value for photo in day.photos):
            await asyncio.to_thread(diary.update_detail, day, "favorite", value)
        elif operation == "remove":
            await asyncio.to_thread(diary.remove_photo, day, value)
        await summary(message, day, diary, replace=True)
    except DraftError as exc:
        # Refresh after a stale operation so buttons refer to the latest draft.
        current = await asyncio.to_thread(diary.draft, owner)
        error = ERRORS.get(str(exc), ERRORS["stale"])
        if current:
            await summary(message, current, diary, error, replace=True)
        else:
            await send_home(message, owner, diary, settings, error)


@router.callback_query(F.data.startswith("save:"))
async def save(callback: CallbackQuery, diary: Diary, settings: Settings, albums: "AlbumReplies") -> None:
    await callback.answer()
    day_id = callback.data.split(":", 1)[1]
    owner = callback.from_user.id
    message = callback.message
    if any(saved_owner == owner for saved_owner, _ in albums.pending):
        active = await asyncio.to_thread(diary.draft, owner)
        if active and active.id == day_id:
            await reply(message, PROMPTS["album_pending"])
            return
    existing = (await asyncio.to_thread(diary.get, owner, day_id)) if settings.first_save_sticker_id else None
    try:
        day = await asyncio.to_thread(diary.save, owner, day_id)
    except Exception as exc:
        if isinstance(exc, DraftError):
            notice = ERRORS.get(str(exc), ERRORS["build"])
        else:
            logger.error("Scene generation failed (%s)", type(exc).__name__)
            notice = ERRORS["build"]
        draft = await asyncio.to_thread(diary.draft, owner)
        if draft:
            await summary(message, draft, diary, notice)
        else:
            await send_home(message, owner, diary, settings, notice)
        return
    await reply(message, PROMPTS["saved"].format(title=escape(day.title)), keyboard(
        (web_link("day", settings.webapp_url, day.id),), (web_link("to_archive", settings.webapp_url),),
        (action(LABELS["new"], "draft:new"),),
    ), replace=True)
    if settings.first_save_sticker_id and not existing and await asyncio.to_thread(diary.first_saved_id, owner) == day.id:
        await send_optional_sticker(message, settings.first_save_sticker_id)
