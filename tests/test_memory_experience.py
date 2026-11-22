import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException

from app.infrastructure.db.database import open_database
from app.infrastructure.media.storage import MediaStore
from app.services.diary import Diary
from app.web.routes.capture import current
from app.web.routes.diary import media
from app.web.routes.films import Edit, Item, build, delete_film, get_film
from app.web.routes.library import Metadata, Version, delete_day, metadata
from app.web.routes.remix import Link, change_link, remix
from config.settings import ROOT
from demo.score import make_score


class FilmLibraryTests(unittest.TestCase):
    def setUp(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.path = Path(root.name)
        self.diary = self.reopen()
        for story in ["Шли по парку и пили какао.", "Всю ночь торопились. Отправили."]:
            draft = self.diary.draft(110, create=True)
            self.diary.edit(draft, story=story)
            self.diary.add_photo(draft, (ROOT / "demo/photos/park-1.jpg").read_bytes(), "")
            self.diary.set_track(
                draft,
                {
                    "kind": "link",
                    "title": "Мой трек",
                    "url": "https://example.org/recording",
                    "profile": "calm",
                    "signal": "user",
                },
            )
            self.diary.save(110, draft.id)
        self.days = self.diary.archive(110)
        self.edit = Edit(items=[Item(day=d.id) for d in self.days])

    def reopen(self):
        sessions = open_database(self.path, True)
        self.addCleanup(sessions.kw["bind"].dispose)
        return Diary(sessions, MediaStore(self.path / "media"), "Asia/Almaty")

    def test_saved_movie_is_scoped_and_protects_its_sources(self):
        film = build("save", self.edit, 110, self.diary)
        restored = get_film(film["id"], 110, self.reopen())
        self.assertEqual(restored, film)
        self.assertEqual(
            sorted({shot["day"] for shot in film["shots"]}), sorted(day.id for day in self.days)
        )
        self.assertEqual(film["tracks"], {})
        with self.assertRaises(HTTPException) as error:
            get_film(film["id"], 111, self.diary)
        self.assertEqual(error.exception.status_code, 404)
        with self.assertRaises(HTTPException):
            build("save", self.edit, 111, self.diary)
        day = self.days[0]
        version = Version(revision=day.revision)
        with self.assertRaises(HTTPException):
            delete_day(day.id, version, 110, self.diary)
        delete_film(film["id"], 110, self.diary)
        delete_day(day.id, version, 110, self.diary)
        self.assertFalse((self.diary.media.root / day.id).exists())

    def test_replacement_is_a_proposal_until_commit(self):
        day = self.days[0]
        selection = Link(url="https://example.org/new-song", profile="rhythmic")
        candidate = change_link(day.id, selection, 110, self.diary)
        self.assertNotEqual(
            candidate["scene"]["signals"]["baseSeconds"], day.scene["signals"]["baseSeconds"]
        )
        self.assertEqual(self.diary.get(110, day.id).track, day.track)
        updated, _ = self.diary.commit_preview(110, day.id, candidate["previewToken"])
        self.assertEqual(updated.track["url"], selection.url)
        meta = Metadata(
            revision=updated.revision, date="2024-02-29", title="Зимний парк", reflection="Тихо."
        )
        metadata(day.id, meta, 110, self.diary)
        self.assertEqual(self.diary.get(110, day.id).memory_date.isoformat(), "2024-02-29")
        with self.assertRaises(HTTPException):
            metadata(day.id, meta, 110, self.diary)

    def test_unpublished_photo_is_only_available_to_its_owner(self):
        draft = self.diary.draft(110, create=True)
        self.diary.add_photo(draft, (ROOT / "demo/photos/park-2.jpg").read_bytes(), "")
        asset = draft.photos[0]["id"]
        self.assertEqual(media(draft.id, asset, 110, self.diary).media_type, "image/jpeg")
        self.assertEqual(media(draft.id, asset, 110, self.diary, preview=True).media_type, "image/webp")
        with self.assertRaises(HTTPException):
            media(draft.id, asset, 111, self.diary)
        with self.assertRaises(HTTPException):
            media(draft.id, asset, 111, self.diary, preview=True)
        with self.assertRaises(HTTPException):
            current(self.diary, 111, draft.id, draft.revision)

    def test_second_soundtrack_preserves_primary_and_follows_published_captions(self):
        day = self.days[0]
        candidate = remix(
            self.diary, 110, day.id,
            {"kind": "file", "profile": "rhythmic", "signal": "user", "title": "Второй трек"},
            make_score("rhythmic"), slot="alternate",
        )
        alternate = candidate["comparison"]
        asset_id = alternate["track"]["asset"].rsplit("/", 1)[1]
        self.assertEqual(media(day.id, asset_id, 110, self.diary).media_type, "audio/wav")
        with self.assertRaises(HTTPException):
            media(day.id, asset_id, 111, self.diary)
        self.assertFalse(self.diary.get(110, day.id).comparison)
        updated, _ = self.diary.commit_preview(110, day.id, candidate["previewToken"])
        self.assertEqual(updated.scene, day.scene)
        self.assertEqual(updated.track, day.track)
        self.assertEqual(
            [(frame["asset"], frame["caption"]) for frame in updated.scene["frames"]],
            [(frame["asset"], frame["caption"]) for frame in updated.comparison["frames"]],
        )
        self.assertNotEqual(updated.scene["signals"]["baseSeconds"], updated.comparison["signals"]["baseSeconds"])
        key = updated.scene["frames"][0]["asset"] + ":0"
        _, edited = self.diary.preview_scene(110, day.id, {"captions": {key: "Новая подпись"}})
        self.assertEqual(edited["scene"]["frames"][0]["caption"], "Новая подпись")
        self.assertEqual(edited["comparison"]["frames"][0]["caption"], "Новая подпись")

    def test_caption_correction_and_film_reedit_are_versioned(self):
        day = self.days[0]
        key = day.photos[0]["id"] + ":0"
        saved, candidate = self.diary.preview_scene(110, day.id, {"captions": {key: "Моя подпись"}})
        self.assertEqual(candidate["scene"]["frames"][0]["caption"], "Моя подпись")
        self.assertNotEqual(saved.scene["frames"][0]["caption"], "Моя подпись")
        self.diary.commit_preview(110, day.id, candidate["token"])
        film = build("save", self.edit, 110, self.diary)
        changes = Edit(
            items=self.edit.items, existing=film["id"], revision=1, title="Второй монтаж", music="silent"
        )
        updated = build("save", changes, 110, self.diary)
        self.assertEqual((updated["id"], updated["editRevision"]), (film["id"], 2))
        with self.assertRaises(HTTPException) as stale:
            build("save", changes, 110, self.diary)
        self.assertEqual(stale.exception.status_code, 409)

    def test_studio_preview_retains_media_and_commits_camera_settings(self):
        day = self.days[0]
        photo = day.photos[0]["id"]
        original = day.scene
        choices = {
            "studio": {"order": [photo], "motion": "still", "seconds": 35, "treatment": "graphic"}
        }
        _, candidate = self.diary.preview_scene(110, day.id, choices)
        scene = candidate["scene"]
        self.assertEqual(scene["soundtrack"]["duration"], 35)
        self.assertEqual(scene["treatment"]["style"], "graphic")
        self.assertTrue(
            all(f["motion"] == {"from": 1, "to": 1, "x": 0, "y": 0} for f in scene["frames"])
        )
        self.assertEqual(self.diary.get(110, day.id).scene, original)
        self.diary.commit_preview(110, day.id, candidate["token"])
        persisted = self.reopen().get(110, day.id)
        self.assertEqual(persisted.scene, scene)
        self.assertEqual(persisted.photos, day.photos)
