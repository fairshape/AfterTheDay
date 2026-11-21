from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.copy import LABELS


def action(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=LABELS.get(label, label), callback_data=callback)


def web_link(label: str, base: str, day_id: str = "") -> InlineKeyboardButton:
    url = f"{base}/?day={day_id}" if day_id else f"{base}/"
    return InlineKeyboardButton(text=LABELS[label], web_app=WebAppInfo(url=url))


def keyboard(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows if row])
