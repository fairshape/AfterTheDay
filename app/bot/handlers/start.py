import asyncio
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.copy import ERRORS, PROMPTS
from app.bot.keyboards import action, keyboard, web_link
from app.bot.messages import reply, send_optional_sticker
from app.bot.summaries import show_draft
from app.services.diary import Diary, DraftError
from config.settings import Settings

router = Router(name="start")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)


async def send_home(message: Message, owner: int, diary: Diary, settings: Settings, text: str) -> None:
    draft = await asyncio.to_thread(diary.draft, owner)
    await reply(message, text, keyboard(
        (action("resume", "draft:resume"),) if draft else (),
        (action("new", "draft:new"), web_link("archive", settings.webapp_url, view="journal")),
        (action("🔎 Найти воспоминание", "collection:search"), web_link("⭐ Избранное", settings.webapp_url, view="favorites")),
        (web_link("🎞 Life Replay", settings.webapp_url, view="life"), web_link("🔔 Напоминания", settings.webapp_url, view="reminders")),
    ))


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, diary: Diary, settings: Settings) -> None:
    if command.args == "record":
        day = await asyncio.to_thread(diary.draft, message.from_user.id, create=True)
        today = await asyncio.to_thread(diary.today, message.from_user.id)
        await show_draft(message, day, timezone_year=today.year, webapp_url=settings.webapp_url)
        return
    await send_home(message, message.from_user.id, diary, settings, PROMPTS["welcome"])
    await send_optional_sticker(message, settings.welcome_sticker_id)


@router.message(Command("archive"))
async def archive(message: Message, settings: Settings) -> None:
    await reply(message, PROMPTS["archive"], keyboard((web_link("archive", settings.webapp_url),)))


@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, diary: Diary, settings: Settings) -> None:
    await callback.answer()
    await send_home(callback.message, callback.from_user.id, diary, settings, PROMPTS["welcome"])


@router.message(Command("timezone"))
async def timezone_command(message: Message, command: CommandObject, diary: Diary) -> None:
    if not command.args:
        await reply(message, PROMPTS["timezone"])
        return
    timezone_name = command.args.strip()
    try:
        await asyncio.to_thread(diary.set_timezone, message.from_user.id, timezone_name)
    except DraftError:
        await reply(message, ERRORS["timezone"])
        return
    await reply(message, PROMPTS["timezone_saved"].format(timezone=escape(timezone_name)))
