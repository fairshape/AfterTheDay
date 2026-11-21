from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from app.infrastructure.db.models import Anniversary, Day, Delivery, UserPreference

MOODS = {"уют": ("уют", "какао", "согрев"), "радость": ("радост", "смех", "расхохот", "весел"),
         "спокойствие": ("спокой", "тишин", "тихо"), "ностальгия": ("ностальг", "скучаю", "детств"),
         "напряжение": ("напряж", "тороп", "тревож"), "облегчение": ("облегч", "выдох", "отправили"),
         "грусть": ("груст", "печал")}


def tags(day):
    if day.mood_tags is not None:
        return day.mood_tags
    words = (day.story + " " + day.details.get("mood", "")).casefold().replace("ё", "е")
    return [label for label, cues in MOODS.items() if any(cue in words for cue in cues)]


def occurrence(event, year):
    return date(year, event.month, min(event.day, monthrange(year, event.month)[1]))


def due(day, reminder, zone):
    return datetime.combine(occurrence(day.memory_date, reminder.year), time.fromisoformat(reminder.clock), ZoneInfo(zone))


def schedule(db, day, zone, clock="19:00", now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(zone))
    year = max(day.memory_date.year + 1, local.year)
    if datetime.combine(occurrence(day.memory_date, year), time.fromisoformat(clock), local.tzinfo) <= local:
        year += 1
    if db.get(Delivery, (day.id, year)):
        year += 1
    db.execute(insert(Anniversary).values(day_id=day.id, year=year, clock=clock).on_conflict_do_nothing())


def new_publication(db, day):
    pref = db.get(UserPreference, day.owner_id)
    if pref and pref.auto_anniversary:
        schedule(db, day, pref.timezone)


def reminder_settings(diary, owner):
    with diary.sessions() as db:
        pref = db.get(UserPreference, owner)
        zone = pref.timezone if pref else str(diary.timezone)
        rows = db.execute(select(Day, Anniversary).join(Anniversary, Anniversary.day_id == Day.id)
                          .where(Day.owner_id == owner, Day.saved_at.is_not(None)))
        items = [{"id": day.id, "title": day.title, "when": due(day, item, zone).isoformat(), "clock": item.clock}
                 for day, item in rows]
        return {"timezone": zone, "auto": bool(pref and pref.auto_anniversary), "titles": bool(pref and pref.show_title),
                "items": sorted(items, key=lambda item: item["when"])}


def change_reminder(diary, owner, day_id, enabled, clock=None):
    with diary.sessions.begin() as db:
        day = db.scalar(select(Day).where(Day.id == day_id, Day.owner_id == owner, Day.saved_at.is_not(None)))
        if not day:
            raise LookupError
        existing = db.get(Anniversary, day_id)
        pref = db.get(UserPreference, owner)
        if enabled and not existing:
            schedule(db, day, pref.timezone if pref else str(diary.timezone), clock or "19:00")
        elif existing and enabled and clock:
            existing.clock = clock
        elif existing and not enabled:
            db.delete(existing)


def claim_due(diary, now):
    """Claim before network I/O. Telegram has no idempotency key for sendMessage."""
    claimed = []
    with diary.sessions.begin() as db:
        rows = db.execute(select(Day, Anniversary, UserPreference).join(Anniversary, Anniversary.day_id == Day.id)
                          .outerjoin(UserPreference, UserPreference.owner_id == Day.owner_id).where(Day.owner_id > 0))
        for day, reminder, pref in rows:
            zone = pref.timezone if pref else str(diary.timezone)
            scheduled = due(day, reminder, zone)
            if scheduled > now:
                continue
            late = now - scheduled > timedelta(hours=24)
            year = reminder.year
            next_year = max(year + 1, now.astimezone(ZoneInfo(zone)).year)
            delivery = db.get(Delivery, (day.id, year))
            if delivery and delivery.status == "retry":
                if not late and delivery.retry_at and delivery.retry_at > now.astimezone(timezone.utc).replace(tzinfo=None):
                    continue
                db.delete(delivery)
                db.flush()
            inserted = db.execute(insert(Delivery).values(day_id=day.id, year=year, status="expired" if late else "claimed")
                                  .on_conflict_do_nothing())
            db.execute(update(Anniversary).where(Anniversary.day_id == day.id, Anniversary.year == year)
                       .values(year=next_year))
            if inserted.rowcount and not late:
                claimed.append((day.id, year, day.owner_id, day.title if pref and pref.show_title else ""))
                break
    return claimed
