import asyncio
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, ForceReply, Message

from app.bot.keyboards import keyboard, action, web_link
from app.bot.messages import reply
from app.services.anniversaries import change_reminder, reminder_settings

router = Router(name="collection")
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
QUESTION = "🔎 Что найти в дневнике?\nПришли слово, место, дату или настроения через запятую."


@router.callback_query(F.data == "collection:search")
async def ask(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(QUESTION, reply_markup=ForceReply(input_field_placeholder="Слово, место или дата"))


async def results(message, diary, settings, query):
    days = await asyncio.to_thread(diary.archive, message.from_user.id, query)
    title = "🔎 <b>Найденные воспоминания</b>" if days else "🔎 <b>Совпадений пока нет</b>"
    rows = [(web_link(f"{day.memory_date:%d.%m.%Y} · {day.title}", settings.webapp_url, day.id),) for day in days[:5]]
    await reply(message, title, keyboard(*rows, (action("Другой запрос", "collection:search"),
                web_link("Все фильтры", settings.webapp_url, view="search")), (action("home","home"),)))


@router.message(Command("find"))
async def find(message: Message, command: CommandObject, diary, settings):
    if command.args:
        await results(message, diary, settings, command.args[:120])
    else:
        await message.answer(QUESTION, reply_markup=ForceReply())


@router.message(F.reply_to_message.from_user.is_bot, F.reply_to_message.text == QUESTION, F.text)
async def search(message: Message, diary, settings):
    await results(message, diary, settings, message.text[:120])


@router.callback_query(F.data.startswith("ann:"))
async def anniversary(callback: CallbackQuery, diary, settings):
    await callback.answer()
    _, op, day_id = callback.data.split(":", 2)
    owner = callback.from_user.id
    try:
        await asyncio.to_thread(change_reminder, diary, owner, day_id, op == "on")
    except LookupError:
        await reply(callback.message, "Эта запись недоступна.")
        return
    info = await asyncio.to_thread(reminder_settings, diary, owner)
    item = next((item for item in info["items"] if item["id"] == day_id), None)
    rows = []
    text = "🔕 <b>Напоминание отключено</b>"
    if item:
        when = datetime.fromisoformat(item["when"])
        text = f"📅 <b>Годовщина в календаре</b>\n{when:%d.%m.%Y в %H:%M} · {escape(info['timezone'])}"
        rows.append((action("Отменить напоминание", f"ann:off:{day_id}"),))
    rows.append((web_link("🔔 Напоминания", settings.webapp_url, view="reminders"),))
    await reply(callback.message, text, keyboard(*rows))
