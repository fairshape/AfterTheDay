import json
import re

from app.infrastructure.db.models import Day
from config.settings import ROOT

catalog = json.loads((ROOT / "web" / "art" / "catalog.json").read_text(encoding="utf-8"))
COLORS = {color["id"]: color["hex"] for color in catalog["colors"]}
STICKERS = {sticker["id"]: re.compile(rf"(?:^|[^a-zа-яё])(?:{sticker['pattern']})", re.IGNORECASE) for sticker in catalog["stickers"]}


def rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index+2], 16) for index in (1, 3, 5))


def suggest_color(day: Day) -> str:
    accent = rgb(day.scene.get("palette", {}).get("accent", "#AA89FF"))
    return min(COLORS, key=lambda key: sum((a - b) ** 2 for a, b in zip(accent, rgb(COLORS[key]))))


def suggest_sticker(day: Day) -> str:
    description = " ".join(str(day.details.get(key, "")) for key in ("weather", "time", "key_detail", "place"))
    material = f"{description} {day.story}"
    return next((name for name, pattern in STICKERS.items() if pattern.search(material)), "spark")


def original_cover(day: Day) -> dict[str, str]:
    direction = day.details.get("_art_direction", {})
    color = direction.get("color")
    sticker = direction.get("sticker")
    return {
        "color": color if color in COLORS else suggest_color(day),
        "sticker": sticker if sticker in STICKERS else suggest_sticker(day),
        "photo": day.scene.get("cover") or day.photos[0]["id"],
    }
