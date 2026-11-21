from html import escape

from aiogram.types import InlineKeyboardButton, Message

from app.bot.copy import LABELS, MONTHS, MOODS, PROMPTS, STATUS, WEATHER
from app.bot.keyboards import action, keyboard, song_options, web_link
from app.bot.messages import reply
from app.infrastructure.db.models import Day
from app.services.diary import TRACK_STEPS, missing_step
from app.services.music import track_link
from app.services.context import visible_place


async def show_draft(message: Message, day: Day, notice: str = "", *, timezone_year: int, replace: bool = False, webapp_url: str = "") -> None:
    context = [f"{day.memory_date.day} {MONTHS[day.memory_date.month - 1]}"]
    if day.memory_date.year != timezone_year:
        context[0] += f" {day.memory_date.year}"
    context.extend(value for value in (day.details.get("time"), visible_place(day.details),
                                        day.details.get("weather"), day.details.get("mood")) if value)
    song_url = track_link(day.track.get("url", "")) if day.track.get("kind") == "link" else None
    status = [
        STATUS["story_added" if day.story else "no_story"],
        STATUS["photo_count"].format(count=len(day.photos)) if day.photos else STATUS["no_photos"],
        STATUS["track_linked" if song_url else "track_added" if day.track else "no_track"],
    ]
    step = day.step or missing_step(day) or "ready"
    rows = []
    if step == "story":
        caption = next((photo for photo in day.photos if photo["caption"].strip()
                        and not track_link(photo["caption"].strip())), None)
        if caption:
            rows.append((action("use_caption", f"caption:{caption['id']}"),))
    if step == "profile":
        rows.extend([tuple(action(profile, f"profile:{profile}") for profile in ("calm", "rhythmic", "tense")),
                     (action("rising", "profile:rising"),)])
    elif step == "ready":
        primary = web_link("preview", webapp_url, day.id, preview=True) if webapp_url else action("save", f"save:{day.id}")
        rows.extend([(primary,), (action("edit", "draft:edit"), action("details", "draft:details"))])

    if step in TRACK_STEPS or step == "track":
        rows.extend(song_options())
        if step in TRACK_STEPS:
            rows.append((action("back", "draft:back"),))
    elif step in {"date", "time", "place", "place_label", "weather", "mood", "key_detail", "cue", "favorite"}:
        if step == "date":
            rows.append((action("today", "date:today"), action("yesterday", "date:yesterday")))
        if step == "weather":
            rows.append(tuple(action(label, f"weather:{key}") for key, label in WEATHER.items()))
        if step == "mood":
            rows.append(tuple(action(label.capitalize(), f"mood:{key}") for key, label in MOODS.items()))
        if step == "favorite":
            rows.extend(photo_buttons(day, "favorite"))
        if ((step == "date" and (day.details.get("event_date") or "_creation_date" not in day.details))
                or (step in {"place", "place_label"} and day.details.get("coordinates")) or step in day.details
                or (step == "favorite" and "favorite_photo" in day.details) or (step == "cue" and day.track.get("cue"))):
            rows.append((action("clear", f"clear:{step}"),))
        rows.append((action("skip", "draft:back"), action("back_details", "draft:details")))
    elif step == "photo_edit":
        rows.extend(photo_buttons(day, "remove"))
        rows.append((action("back", "draft:back"),))
    elif step.endswith("_edit"):
        rows.append((action("back", "draft:back"),))
    elif step != "ready":
        rows.append((action("edit", "draft:edit"),))

    linked_review = song_url and step in {"profile", "ready"}
    if linked_review:
        rows.append((InlineKeyboardButton(text=LABELS["open_song"], url=song_url),
                     action("upload_song", "song:file")))
    rows.append((action("cancel", "draft:cancel"), action(LABELS["home"], "home")))
    duration = day.track.get("duration", 0)
    prompt = PROMPTS[step].format(duration=f"{int(duration) // 60}:{int(duration) % 60:02}")
    summary = "\n".join([*(status[1:] if step == "ready" else status), escape(" · ".join(context))])
    parts = [escape(notice), prompt, summary]
    if linked_review:
        parts.append(PROMPTS["linked_playback"])
    if step == "story_edit" and day.story:
        current = f"«{day.story[:500]}{'…' if len(day.story) > 500 else ''}»"
        parts.append(STATUS["current"].format(value=escape(current)))
    if step == "track_edit" and day.track:
        parts.append(STATUS["current"].format(value=escape(day.track["title"])))
    if step in {"key_detail", "time", "place", "weather", "mood"} and day.details.get(step):
        parts.append(STATUS["current"].format(value=escape(day.details[step])))
    await reply(message, "\n\n".join(part for part in parts if part), keyboard(*rows), replace=replace)


def photo_buttons(day: Day, operation: str):
    buttons = [action(STATUS["remove_photo"].format(index=index) if operation == "remove" else f"№{index}",
                      f"{operation}:{photo['id']}")
               for index, photo in enumerate(day.photos, 1)]
    return [tuple(buttons[index:index + 3]) for index in range(0, len(buttons), 3)]
