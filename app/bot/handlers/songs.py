import asyncio
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from app.bot.copy import ERRORS, LABELS, PROMPTS
from config.settings import Settings
from app.bot.handlers.draft import summary
from app.bot.keyboards import action, keyboard, song_options
from app.bot.messages import reply
from app.infrastructure.db.models import Day
from app.services.diary import Diary, DraftError
from app.services.song_search import CatalogueUnavailable, SongSearch

router = Router(name="songs")
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)


async def show_results(message: Message, day: Day, query: str, search: SongSearch) -> None:
    if not 2 <= len(query) <= 120:
        await reply(message, ERRORS["song_query"], keyboard(*song_options()))
        return
    try:
        results = await search.find(query)
    except CatalogueUnavailable:
        await reply(message, ERRORS["catalogue"], keyboard(*song_options()))
        return
    if not results:
        await reply(message, ERRORS["no_songs"], keyboard(*song_options()))
        return
    token = search.offer(day, results)
    rows = []
    lines = []
    for index, song in enumerate(results, 1):
        version = f" · {escape(song.album)}" if song.album else ""
        lines.append(f"{index}. <b>{escape(song.title)}</b> · {escape(song.artist)}{version}")
        rows.append((
            action(f"{index}. {song.title} · {song.artist}"[:58], f"song:pick:{token}:{index - 1}"),
            InlineKeyboardButton(text=LABELS["open_song"], url=song.url),
        ))
    await reply(message, f"{PROMPTS['song_results']}\n\n" + "\n".join(lines), keyboard(*rows, *song_options()))


@router.callback_query(F.data.startswith("song:"))
async def song_action(callback: CallbackQuery, diary: Diary, song_search: SongSearch, settings: Settings) -> None:
    owner = callback.from_user.id
    day = await asyncio.to_thread(diary.draft, owner)
    if not day:
        await callback.answer(ERRORS["song_stale"])
        return
    operation, *choice = callback.data.split(":")[1:]
    if operation == "pick":
        token, index = choice if len(choice) == 2 else ("", "")
        song = song_search.choose(day, token, int(index) if index.isascii() and index.isdigit() and len(index) == 1 else -1)
        if not song or day.step != "track_search":
            await callback.answer(ERRORS["song_stale"], show_alert=True)
            return
        try:
            await asyncio.to_thread(diary.set_track, day, song.attachment())
        except DraftError:
            await callback.answer(ERRORS["song_stale"], show_alert=True)
            return
    elif operation in {"search", "link", "file"}:
        await asyncio.to_thread(diary.edit, day, step=f"track_{operation}")
    else:
        await callback.answer()
        return
    await callback.answer()
    await summary(callback.message, day, diary, replace=True, webapp_url=settings.webapp_url)
