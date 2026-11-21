from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.infrastructure.db.database import open_database
from app.infrastructure.db.models import Anniversary, Day, Delivery, UserPreference
from app.infrastructure.media.storage import MediaStore
from app.services.anniversaries import change_reminder, claim_due, schedule
from app.services.diary import Diary


class AnnualReminderTests(unittest.TestCase):
    def setUp(self):
        storage = TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        self.path = Path(storage.name)
        self.diary = self.reopen()
        self.now = datetime(2027, 2, 28, 14, tzinfo=timezone.utc)
        self.day = Day(id="one", owner_id=10, created_at=self.now, saved_at=self.now,
                       memory_date=date(2024, 2, 29), title="Название личной записи")
        with self.diary.sessions.begin() as db:
            db.add(self.day)
            db.add(UserPreference(owner_id=10, timezone="Asia/Almaty"))
            schedule(db, self.day, "Asia/Almaty", now=self.now - timedelta(days=2))

    def reopen(self):
        sessions = open_database(self.path, True)
        self.addCleanup(sessions.kw["bind"].dispose)
        return Diary(sessions, MediaStore(self.path / "media"), "Asia/Almaty")

    def test_once_after_restart_and_local_time(self):
        self.assertFalse(claim_due(self.diary, self.now - timedelta(seconds=1)))
        diary = self.reopen()
        self.assertEqual(claim_due(diary, self.now + timedelta(hours=2)), [("one", 2027, 10, "")])
        self.assertFalse(claim_due(self.reopen(), self.now + timedelta(hours=3)))
        with diary.sessions() as db:
            self.assertEqual(db.get(Anniversary, "one").year, 2028)
            self.assertIsNotNone(db.get(Delivery, ("one", 2027)))

    def test_expiry_cancel_and_ownership(self):
        with self.assertRaises(LookupError):
            change_reminder(self.diary, 11, "one", False)
        self.assertFalse(claim_due(self.diary, self.now + timedelta(hours=25)))
        with self.diary.sessions() as db:
            self.assertEqual(db.get(Delivery, ("one", 2027)).status, "expired")
        change_reminder(self.diary, 10, "one", False)
        with self.diary.sessions() as db:
            self.assertIsNone(db.get(Anniversary, "one"))

    def test_future_publications_follow_opt_in_and_delivery_action(self):
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch

        from app.bot.anniversaries import dispatch
        from app.services.anniversaries import new_publication

        with self.diary.sessions.begin() as db:
            db.get(UserPreference, 10).auto_anniversary = True
            second = Day(id="two", owner_id=10, created_at=self.now, saved_at=self.now,
                         memory_date=date(2024, 4, 2), title="Ещё один день")
            db.add(second)
            new_publication(db, second)
            self.assertIsNotNone(db.get(Anniversary, "two"))
        bot = AsyncMock()
        settings = SimpleNamespace(webapp_url="https://diary.example.org", anniversary_sticker_id="")
        with patch("app.bot.anniversaries.datetime") as clock, patch(
                "app.bot.anniversaries.asyncio.sleep", side_effect=asyncio.CancelledError):
            clock.now.return_value = self.now
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(dispatch(bot, self.diary, settings))
        bot.send_message.assert_awaited_once()
        args = bot.send_message.await_args
        self.assertEqual(args.args, (10, "📅 Годовщина воспоминания"))
        self.assertEqual(args.kwargs["reply_markup"].inline_keyboard[0][0].web_app.url,
                         "https://diary.example.org/?day=one")
        with self.diary.sessions() as db:
            self.assertEqual(db.get(Delivery, ("one", 2027)).status, "sent")
