import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from app.bot.keyboards import keyboard, web_link
from app.services.anniversaries import claim_due
from app.infrastructure.db.models import Anniversary, Delivery

logger = logging.getLogger(__name__)


async def dispatch(bot, diary, settings):
    while True:
        try:
            items = await asyncio.to_thread(claim_due, diary, datetime.now(timezone.utc))
            for day_id, year, owner, title in items:
                status = "uncertain"
                try:
                    await bot.send_message(owner, "📅 Годовщина воспоминания" + (f"\n{title}" if title else ""),
                                           reply_markup=keyboard((web_link("day", settings.webapp_url, day_id),)))
                    status = "sent"
                    if settings.anniversary_sticker_id:
                        await bot.send_sticker(owner, settings.anniversary_sticker_id)
                except TelegramRetryAfter as error:
                    if status != "sent":
                        with diary.sessions.begin() as db:
                            reminder = db.get(Anniversary, day_id)
                            if reminder and reminder.year == year + 1:
                                reminder.year = year
                                delivery = db.get(Delivery, (day_id, year))
                                delivery.retry_at = datetime.now(timezone.utc) + timedelta(seconds=error.retry_after + 1)
                                status = "retry"
                                delivery.status = status
                except TelegramAPIError as exc:
                    logger.warning("Anniversary delivery %s", type(exc).__name__)
                with diary.sessions.begin() as db:
                    db.get(Delivery, (day_id, year)).status = status
            if items:
                await asyncio.sleep(.1)
                continue
        except Exception as exc:
            logger.error("Anniversary worker %s", type(exc).__name__)
        await asyncio.sleep(45)
