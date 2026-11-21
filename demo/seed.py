from datetime import date
import logging

from sqlalchemy import update

from app.infrastructure.audio.speech import SpeechUnavailable
from app.infrastructure.db.models import Day
from app.services.narration import suggested_rate

from app.services.diary import DEMO_OWNER, Diary
from config.settings import ROOT
from demo.score import make_score

logger = logging.getLogger(__name__)

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
        "composition": "rain",
        "cue": 0.0,
        "captions": ("Окно автобуса запотело", "Какао всё ещё обжигало ладони", "Фонарь дрожал в луже"),
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
    {
        "date": "2026-11-05", "images": "platform", "count": 2, "profile": "rhythmic", "track": "До поезда",
        "story": "Письмо на пустой платформе. Я тихо ждал поезд на скамейке. В наушниках стучал быстрый ритм. Я скучал и держал закрытый конверт. Письмо так и не открыл.",
        "details": {"mood": "грусть и ностальгия"},
        "style": {}, "composition": "rhythmic",
    },
    {
        "date": "2026-11-02", "images": "dawn", "profile": "rising", "track": "Город просыпается",
        "story": "Первый свет над городом. В окне было ещё сумрачно, но на соседней стене появилось золотое пятно. Потом свет дошёл до крыш.",
        "details": {"time": "раннее утро", "mood": "всё постепенно просыпалось"},
        "style": {}, "composition": "dawn",
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
        for index in range(1, example.get("count", 3) + 1):
            photo = ROOT / "demo" / "photos" / f"{example['images']}-{index}.jpg"
            captions = example.get("captions", ())
            diary.add_photo(day, photo.read_bytes(), captions[index - 1] if captions else "", index)
        if "favorite" in example:
            details["favorite_photo"] = day.photos[example["favorite"]]["id"]
        diary.edit(day, details=details)
        profile = example["profile"]
        cue = {"cue": example["cue"]} if "cue" in example else {}
        diary.set_track(day, {"kind": "file", "title": example["track"], "profile": profile,
                             "signal": "demo_score", **cue}, make_score(example.get("composition", profile)))
        alternate = None
        alternate_title = example.get("alternate") or ("Огни на ходу" if example["images"] == "rain" else "")
        if alternate_title:
            alternate = {**diary.media.ingest(day.id, make_score("rhythmic"), "audio"),
                         "kind": "file", "title": alternate_title, "profile": "rhythmic", "signal": "demo_score"}
        diary.save(DEMO_OWNER, day.id, comparison=alternate)

    if not diary.voice:
        return
    available = diary.voice.provider.available()
    if not available:
        return
    examples_by_story = {example["story"]: example for example in EXAMPLES}
    for day in diary.archive(DEMO_OWNER):
        example = examples_by_story.get(day.story)
        if not example or day.narration or day.scene.get("version") != 2 or example["images"] not in {"park", "kitchen", "deadline"}:
            continue
        voice = "denis" if example["images"] == "deadline" else "irina"
        try:
            narration = diary.voice.build(day, day.scene, voice if voice in available else available[0],
                                          suggested_rate(day, day.scene), {})
            with diary.sessions.begin() as db:
                db.execute(update(Day).where(Day.id == day.id, Day.revision == day.revision,
                                             Day.owner_id == DEMO_OWNER).values(narration=narration))
        except SpeechUnavailable:
            logger.warning("Demo speech could not be generated")
