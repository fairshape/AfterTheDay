import re
from dataclasses import dataclass

from PIL import Image, ImageOps, ImageStat

from app.infrastructure.media.storage import MediaStore


@dataclass(frozen=True)
class Rhythm:
    seconds: float
    transition: float
    zoom: float
    drift: float


RHYTHMS = {
    "calm": Rhythm(5.0, 0.85, 1.05, 0.65),
    "rhythmic": Rhythm(2.65, 0.27, 1.12, 2.2),
    "tense": Rhythm(1.85, 0.13, 1.055, 1.7),
}
SETTLING = re.compile(r"\b(?:отправили|сдали|успели|наконец|выдохнули|submitted|finally)\b", re.I)
LEAD_INS = re.compile(r"^(?:сегодня|потом|в общем|кажется|я помню|мы помним|today)\b[ ,]*", re.I)
WEATHER_TEXTURE = re.compile(r"дожд|туман|снег|измороз", re.I)
QUIET_MOOD = re.compile(r"спокой|тихо|нежн|устал|peace|quiet", re.I)


def excerpts(story: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?…])\s+|\n+", story.strip())
    phrases = []
    for sentence in sentences:
        fragments = re.split(r"\s+[—–]\s+|;\s+|,\s+(?=а\s|но\s|потом\s)", sentence)
        for fragment in fragments:
            words = fragment.strip(" ,.;!?…—–").split()
            while words:
                excerpt_words = words[:10]
                excerpt = " ".join(excerpt_words)
                while len(excerpt) > 108 and len(excerpt_words) > 1:
                    excerpt_words.pop()
                    excerpt = " ".join(excerpt_words)
                phrases.append(excerpt[:108])
                words = words[len(excerpt_words):]
    return phrases or [story.strip()[:108]]


def story_title(phrases: list[str]) -> str:
    for phrase in phrases:
        candidate = LEAD_INS.sub("", phrase).strip()
        if 3 <= len(candidate.split()) <= 7 and len(candidate) <= 78:
            return candidate[0].upper() + candidate[1:]
    chosen = max(phrases[:8], key=lambda phrase: min(len(phrase.split()), 7))
    words = chosen.split()[:7]
    title = " ".join(words)[:78].rstrip(" ,")
    if len(words) < 3:
        return f'В памяти осталось «{title}»'
    return title[0].upper() + title[1:]


def photo_palette(media: MediaStore, day_id: str, photos: list[dict]) -> dict:
    # Equal-sized contact sheets give each source photo an equal vote.
    sheet = Image.new("RGB", (24 * len(photos), 24))
    for index, photo in enumerate(photos):
        with Image.open(media.path(day_id, photo["id"])) as source:
            oriented = ImageOps.exif_transpose(source)
            sheet.paste(oriented.convert("RGB").resize((24, 24), Image.Resampling.BOX), (index * 24, 0))
    stats = ImageStat.Stat(sheet.convert("L"))
    indexed = sheet.quantize(colors=8)
    swatches = indexed.getpalette()
    ranked = sorted(indexed.getcolors(), reverse=True)
    dominant = swatches[ranked[0][1] * 3:ranked[0][1] * 3 + 3]
    candidates = [swatches[i * 3:i * 3 + 3] for _, i in ranked]
    accent = max(candidates, key=lambda color: (max(color) - min(color)) * 2 + sum(color) / 3)

    def hex_color(channels):
        return "#" + "".join(f"{int(channel):02x}" for channel in channels)

    shadow_gain = 0.28 + min(stats.stddev[0] / 320, 0.14)
    accent_lift = 44 + (255 - stats.mean[0]) * 0.075
    return {
        "background": hex_color(min(93, channel * shadow_gain + 10) for channel in dominant),
        "accent": hex_color(min(255, channel * 0.77 + accent_lift) for channel in accent),
        "ink": "#fff9ed",
        "brightness": round(stats.mean[0]),
        "contrast": round(stats.stddev[0]),
    }


def build_scene(media: MediaStore, day_id: str, story: str, photos: list[dict],
                track: dict, details: dict, *, base: dict | None = None) -> dict:
    phrases = excerpts(story)
    title = base["title"] if base else story_title(phrases)
    palette = base["palette"] if base else photo_palette(media, day_id, photos)
    profile = track["profile"]
    rhythm = RHYTHMS[profile]
    quiet = bool(QUIET_MOOD.search(details.get("mood", "")))
    grain = 0.16 if WEATHER_TEXTURE.search(details.get("weather", "")) else 0.09
    favorite = details.get("favorite_photo")
    pin = details.get("key_detail", "").strip()[:108]
    last_turn = next((phrase for phrase in reversed(phrases) if SETTLING.search(phrase)), "")
    release = bool(last_turn and profile == "tense")
    closing_detail = details.get("_closing_detail", "")

    frame_count = max(2, len(photos), min(4, len(phrases)))
    caption_count = min(3 if pin else 4, len(phrases), frame_count)
    captions = {}
    for index in range(caption_count):
        frame = round(index * (frame_count - 1) / max(1, caption_count - 1))
        phrase_index = round(index * (len(phrases) - 1) / max(1, caption_count - 1))
        captions[frame] = phrases[phrase_index]
    photo_order = [photos[min(index, len(photos) - 1)]["id"] for index in range(frame_count)]
    focus_index = photo_order.index(favorite) if favorite in photo_order else frame_count - 1
    if pin:
        captions[focus_index] = pin
    if release and (not pin or focus_index != frame_count - 1):
        captions[frame_count - 1] = last_turn

    if closing_detail:
        captions[frame_count - 1] = closing_detail

    frames = []
    for index, photo_id in enumerate(photo_order):
        settles = release and index == frame_count - 1
        focused = index == focus_index and bool(favorite or pin)
        seconds = rhythm.seconds * (0.93 if index % 2 else 1) + (1.25 if focused else 0)
        if settles or (closing_detail and index == frame_count - 1):
            seconds = max(seconds, 5.7 if profile == "calm" else 4.5)
        zoom = 1 if settles else 1 + (rhythm.zoom - 1) * (0.55 if quiet else 1)
        drift = 0 if settles else rhythm.drift * (-1 if index % 2 else 1)
        frames.append({
            "asset": photo_id,
            "seconds": round(seconds, 2),
            "caption": captions.get(index, ""),
            "transition": rhythm.transition,
            "motion": {"from": 1.017 if len(photos) == 1 and index % 2 and not settles else 1,
                       "to": round(zoom, 3), "x": drift, "y": -abs(drift) / 2},
        })

    return {
        "version": 1,
        "title": title,
        "cover": photos[0]["id"],
        "palette": palette,
        "grain": grain,
        "frames": frames,
        "track": track,
        "signals": {
            "story": last_turn if release else pin or next(iter(captions.values()), ""),
            "focus": "release" if release else "pin" if pin or favorite else "excerpt",
            "pinText": pin,
            "photoCount": len(photos),
            "profile": profile,
            "source": track["signal"],
            "baseSeconds": rhythm.seconds,
            "transition": rhythm.transition,
            "motion": max(frame["motion"]["to"] for frame in frames),
        },
    }
