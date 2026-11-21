import asyncio

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery

from app.bot.handlers.draft import summary
from app.services.diary import Diary
from config.settings import Settings

router = Router(name="songs")
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)


@router.callback_query(F.data.startswith("song:"))
async def song_action(callback: CallbackQuery, diary: Diary, settings: Settings) -> None:
    day = await asyncio.to_thread(diary.draft, callback.from_user.id)
    if not day:
        await callback.answer("Открой или создай черновик.")
        return
    operation = callback.data.split(":")[1]
    if operation in {"search", "pick"}:  # Old messages may still contain catalogue buttons.
        await callback.answer("Пришли ссылку на песню или аудиофайл.")
    else:
        await callback.answer()
    if operation in {"search", "pick", "link", "file"}:
        await asyncio.to_thread(diary.edit, day, step="track_file" if operation == "file" else "track_link")
        await summary(callback.message, day, diary, replace=True, webapp_url=settings.webapp_url)
