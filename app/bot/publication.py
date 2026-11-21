from html import escape
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from app.bot.copy import PROMPTS
from app.bot.keyboards import action, keyboard, web_link
from app.infrastructure.db.models import Day

logger = logging.getLogger(__name__)


async def notify_publication(bot: Bot, origin: str, day: Day, sticker_id: str = "") -> None:
    try:
        await bot.send_message(day.owner_id, PROMPTS["saved"].format(title=escape(day.title)),
                               parse_mode=ParseMode.HTML,
                               reply_markup=keyboard((web_link("day", origin, day.id),),
                                                     (action("📅 Напомнить через год", f"ann:on:{day.id}"),),
                                                     (web_link("to_archive", origin, view="journal"),)))
    except TelegramAPIError as exc:
        logger.warning("Telegram publication notification failed (%s)", type(exc).__name__)
        return
    if sticker_id:
        try:
            await bot.send_sticker(day.owner_id, sticker_id)
        except TelegramAPIError as exc:
            logger.warning("Optional diary sticker could not be sent (%s)", type(exc).__name__)
