from datetime import date

from app.services.diary import DEMO_OWNER, Diary
from config.settings import ROOT
from demo.score import make_score

EXAMPLES = (
    {
        "date": "2026-11-20", "images": "park", "profile": "calm", "track": "Тепло в ладонях",
        "story": "Осенний парк и какао. Под ногами шуршали жёлтые листья. Было холодно, но стакан какао согревал руки. Долго разговаривали.",
        "details": {"mood": "холодный воздух и тепло от разговора"},
        "style": {"sticker": "cup"}, "composition": "park", "alternate": "На шаг быстрее",
    },
    {
        "date": "2026-11-19", "images": "rain", "profile": "calm", "track": "Свет в стекле",
        "story": "Дорога после дождя. Окно автобуса запотело, а какао всё ещё обжигало ладони. Фонарь дрожал в луже у остановки.",
        "details": {"time": "вечер", "place": "Алматы", "weather": "после дождя", "mood": "тихая радость"},
        "style": {"color": "pool", "sticker": "rain"},
        "closing": "Фонарь дрожал в луже",
    },
    {
        "date": "2026-11-08", "images": "kitchen", "profile": "rhythmic", "track": "Ужин на двоих",
        "story": "Смех на кухне. Жарили поздний ужин, спорили, кто порежет лук. Тост подгорел, и тут мы оба расхохотались.",
        "details": {"time": "поздний вечер", "mood": "весело"},
        "style": {"color": "tomato", "sticker": "spark"},
    },
    {
        "date": "2026-11-18", "images": "deadline", "profile": "tense", "track": "До отправки",
        "story": "Ночь в офисе перед сдачей. Светился только экран. На часах было почти три. В наушниках шла электронная музыка. Отправили.",
        "details": {"time": "ночь", "mood": "напряжение"},
        "style": {"sticker": "moon"},
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
                             "signal": "demo_score"}, make_score(example.get("composition", profile)))
        alternate = None
        alternate_title = example.get("alternate") or ("Огни на ходу" if example["images"] == "rain" else "")
        if alternate_title:
            alternate = {**diary.media.ingest(day.id, make_score("rhythmic"), "audio"),
                         "kind": "file", "title": alternate_title, "profile": "rhythmic", "signal": "demo_score"}
        diary.save(DEMO_OWNER, day.id, comparison=alternate)
