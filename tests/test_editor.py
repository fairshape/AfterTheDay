from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.db.database import open_database
from app.infrastructure.media.storage import MediaStore
from app.services.diary import Diary, DraftError
from config.settings import ROOT


class EditorPublicationTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        sessions = open_database(root, True)
        self.addCleanup(sessions.kw["bind"].dispose)
        self.diary = Diary(sessions, MediaStore(root / "media"), "Asia/Almaty")
        day = self.diary.draft(43, create=True)
        self.diary.edit(day, story="Чай остыл на кухне. Долго разговаривали.")
        for index in (1, 2):
            self.diary.add_photo(day, (ROOT / f"demo/photos/kitchen-{index}.jpg").read_bytes(), "")
        self.diary.set_track(day, {"kind": "link", "title": "Песня", "url": "https://example.org/song",
                                  "profile": "calm", "signal": "user"})
        self.day = self.diary.save(43, day.id)
        self.style = {"sticker": "cup", "color": "lilac", "photo": day.photos[0]["id"]}

    def test_failed_speech_leaves_whole_version_playable(self):
        with patch.object(self.diary, "voice") as narration:
            narration.build.side_effect = SpeechUnavailable
            with self.assertRaises(SpeechUnavailable):
                self.diary.set_cover(43, self.day.id, self.style, ["уют"], revision=self.day.revision,
                                     choices={"photo": self.day.photos[0]["id"]}, voice={"voice": "irina", "rate": "slow"})
        saved = self.diary.get(43, self.day.id)
        self.assertEqual((saved.scene, saved.cover_style, saved.mood_tags, saved.revision),
                         (self.day.scene, self.day.cover_style, self.day.mood_tags, self.day.revision))

    def test_stale_and_foreign_saves(self):
        saved = self.diary.set_cover(43, self.day.id, self.style, ["уют"], revision=self.day.revision)
        with self.assertRaisesRegex(DraftError, "stale"):
            self.diary.set_cover(43, self.day.id, {}, [], revision=self.day.revision)
        with self.assertRaisesRegex(DraftError, "missing_day"):
            self.diary.set_cover(44, self.day.id, {}, [], revision=saved.revision)
        self.assertEqual(self.diary.get(43, self.day.id).mood_tags, ["уют"])
