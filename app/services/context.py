from datetime import date
import re

MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
          "сентябрь", "октябрь", "ноябрь", "декабрь")
MONTH_DATES = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
               "сентября", "октября", "ноября", "декабря")
COORDINATE_LABEL = re.compile(r"^[+-]?\d{1,3}\.\d+\s*,\s*[+-]?\d{1,3}\.\d+$")


def visible_place(details: dict) -> str:
    place = details.get("place", "")
    return "" if COORDINATE_LABEL.fullmatch(place.strip()) else place


def date_search(day: date) -> tuple[str, ...]:
    return (
        day.isoformat(), day.strftime("%d.%m.%Y"), day.strftime("%m.%Y"),
        f"{MONTHS[day.month-1]} {day.year}",
        f"{day.day} {MONTH_DATES[day.month-1]} {day.year}",
    )
