from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.copy import LABELS


def action(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=LABELS.get(label, label), callback_data=callback)


def web_link(label: str, base: str, day_id: str = "", *, preview: bool = False) -> InlineKeyboardButton:
    url = f"{base}/?day={day_id}" if day_id else f"{base}/"
    if preview and day_id:
        url += "&preview=1"
    return InlineKeyboardButton(text=LABELS[label], web_app=WebAppInfo(url=url))


def keyboard(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(row) for row in rows if row])

def song_options():
    return ((action("find_song", "song:search"),),
            (action("paste_song", "song:link"), action("upload_song", "song:file")))
