import json
import re

from app.infrastructure.db.models import Day
from config.settings import ROOT

catalog = json.loads((ROOT / "web" / "art" / "catalog.json").read_text(encoding="utf-8"))
COLORS = {color["id"]: color["hex"] for color in catalog["colors"]}
STICKERS = {sticker["id"]: re.compile(rf"(?:^|[^a-zа-яё])(?:{sticker['pattern']})", re.IGNORECASE) for sticker in catalog["stickers"]}


def rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index+2], 16) for index in (1, 3, 5))


def suggest_color(day: Day, scene: dict | None = None) -> str:
    palette = (scene or day.scene).get("palette", {})
    if palette.get("field"):
        return "auto"
    accent = rgb(palette.get("accent", "#AA89FF"))
    return min(COLORS, key=lambda key: sum((a - b) ** 2 for a, b in zip(accent, rgb(COLORS[key]))))


def suggest_sticker(story: str, details: dict) -> str:
    description = " ".join(str(details.get(key, "")) for key in ("weather", "time", "key_detail", "place"))
    material = f"{description} {story}"
    return next((name for name, pattern in STICKERS.items() if pattern.search(material)), "spark")


def original_cover(day: Day, scene: dict | None = None) -> dict[str, str]:
    direction = day.details.get("_art_direction", {})
    color = direction.get("color")
    sticker = direction.get("sticker") or (scene or day.scene).get("sticker")
    return {
        "color": color if color in COLORS else suggest_color(day, scene),
        "sticker": sticker if sticker in STICKERS else suggest_sticker(day.story, day.details),
        "photo": (scene or day.scene).get("cover") or day.photos[0]["id"],
    }
