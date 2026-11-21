import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.infrastructure.db.database import open_database
from app.infrastructure.db.models import UserPreference
from app.infrastructure.media.storage import MediaStore
from app.services.diary import Diary
from app.web.routes.collection import Appearance, appearance, set_appearance
from config.settings import ROOT


class InterfaceThemeTests(unittest.TestCase):
    def test_upgrade_and_account_choice_preserve_existing_preferences(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = open_database(root, False).kw["bind"]
            with original.begin() as connection:
                config = Config(ROOT / "alembic.ini")
                config.attributes["connection"] = connection
                command.upgrade(config, "0008_film_sources")
                connection.execute(text(
                    "INSERT INTO user_preferences (owner_id, timezone, show_title) "
                    "VALUES (42, 'Europe/Paris', 1)"
                ))
            original.dispose()
            sessions = open_database(root, True)
            diary = Diary(sessions, MediaStore(root / "media"), "Asia/Almaty")
            try:
                self.assertEqual(appearance(42, diary).theme, "paper")
                for owner in (42, 84):
                    set_appearance(Appearance(theme="neon"), owner, diary)
                set_appearance(Appearance(theme="paper"), 84, diary)
                self.assertEqual(appearance(42, diary).theme, "neon")
                self.assertEqual(appearance(84, diary).theme, "paper")
                with sessions() as db:
                    pref = db.get(UserPreference, 42)
                    self.assertEqual(pref.timezone, "Europe/Paris")
                    self.assertTrue(pref.show_title)
            finally:
                sessions.kw["bind"].dispose()
