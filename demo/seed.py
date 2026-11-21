from datetime import date

from sqlalchemy import update

from app.infrastructure.db.models import Day
from app.services.scene import build_scene
from app.services.diary import DEMO_OWNER, Diary
from config.settings import ROOT
from demo.score import make_score

EXAMPLES = (
    {
        "date": "2026-11-19", "images": "rain", "profile": "calm", "track": "Свет в стекле",
        "story": "Дорога после дождя. Окно автобуса запотело, а какао всё ещё обжигало ладони. Фонарь дрожал в луже у остановки.",
        "details": {"time": "вечер", "place": "Алматы", "weather": "после дождя", "mood": "тихая радость",
                    "key_detail": "Какао всё ещё обжигало ладони"},
        "favorite": 1, "style": {"color": "pool", "sticker": "rain"},
        "closing": "Фонарь дрожал в луже",
    },
    {
        "date": "2026-11-08", "images": "kitchen", "profile": "rhythmic", "track": "Ужин на двоих",
        "story": "Смех на кухне. Жарили поздний ужин, спорили, кто порежет лук. Тост подгорел, и тут мы оба расхохотались.",
        "details": {"time": "поздний вечер", "mood": "весело"},
        "style": {"color": "tomato", "sticker": "spark"},
    },
    {
        "date": "2026-10-31", "images": "deadline", "profile": "tense", "track": "До отправки",
        "story": "Ночь перед сдачей. В комнате светился только экран. На часах было почти три. Отправили.",
        "details": {"time": "ночь", "mood": "напряжение"},
        "style": {"color": "lilac", "sticker": "moon"},
    },
)


def populate(diary: Diary) -> None:
    existing = {day.memory_date: day for day in diary.archive(DEMO_OWNER)}
    for example in EXAMPLES:
        memory_date = date.fromisoformat(example["date"])
        art_details = {"_art_direction": example["style"]}
        if example.get("closing"):
            art_details["_closing_detail"] = example["closing"]
        if memory_date in existing:
            day = existing[memory_date]
            if "_art_direction" not in day.details and day.story == example["story"]:
                directions = {**day.details, **art_details}
                scene = build_scene(diary.media, day.id, day.story, day.photos, day.track, directions, base=day.scene)
                comparison = (build_scene(diary.media, day.id, day.story, day.photos, day.comparison["track"],
                                          directions, base=scene) if day.comparison else {})
                with diary.sessions.begin() as session:
                    session.execute(update(Day).where(Day.owner_id == DEMO_OWNER, Day.id == day.id,
                                    Day.revision == day.revision).values(
                                    details=directions, scene=scene, comparison=comparison, revision=day.revision + 1))
            continue
        # A partially imported fictional entry can be recreated after interrupted startup.
        unfinished = diary.draft(DEMO_OWNER)
        if unfinished:
            diary.cancel(unfinished)
        day = diary.draft(DEMO_OWNER, create=True)
        details = {**example["details"], **art_details}
        diary.edit(day, memory_date=memory_date, story=example["story"])
        for index in range(1, 4):
            photo = ROOT / "demo" / "photos" / f"{example['images']}-{index}.jpg"
            diary.add_photo(day, photo.read_bytes(), "", index)
        if "favorite" in example:
            details["favorite_photo"] = day.photos[example["favorite"]]["id"]
        diary.edit(day, details=details)
        profile = example["profile"]
        diary.set_track(day, {"kind": "file", "title": example["track"], "profile": profile,
                             "signal": "demo_score"}, make_score(profile))
        alternate = None
        if example["images"] == "rain":
            alternate = {**diary.media.ingest(day.id, make_score("rhythmic"), "audio"),
                         "kind": "file", "title": "Огни на ходу", "profile": "rhythmic", "signal": "demo_score"}
        diary.save(DEMO_OWNER, day.id, comparison=alternate)
