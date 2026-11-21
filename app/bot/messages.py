import logging

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


async def reply(message: Message, text: str, markup: InlineKeyboardMarkup | None = None, *,
                replace: bool = False) -> None:
    if replace and message.text and message.from_user and message.from_user.is_bot:
        try:
            await message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
            return
        except TelegramBadRequest as exc:
            if "message is not modified" in exc.message.lower():
                return
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def send_optional_sticker(message: Message, file_id: str) -> None:
    if file_id:
        try:
            await message.answer_sticker(file_id)
        except TelegramAPIError as exc:
            logger.warning("Optional diary sticker could not be sent (%s)", type(exc).__name__)
