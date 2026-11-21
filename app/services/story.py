import re
from dataclasses import dataclass

TURN = re.compile(r"[,;—]?\s+\b(?:но|зато|вдруг|а потом|и наконец)\s+", re.I)
RELEASE = re.compile(r"\b(?:отправили|сдали|успели|выдохнули|закончили|submitted)\b", re.I)
CLOSENESS = re.compile(r"\b(?:какао|кружк\w*|обня\w*|ладон\w*|разговаривал\w*)\b", re.I)
RESTLESS = re.compile(r"напряж|тревож|тревог|нерв|спеш|торопил|резк", re.I)
QUIET = re.compile(r"спокой|тихо|нежн|устал|молча|тишин|peace|quiet", re.I)
LEAD_IN = re.compile(r"^(?:сегодня|потом|в общем|кажется|я помню|мы помним|today)\b[ ,]*", re.I)


@dataclass(frozen=True)
class StoryArc:
    title: str
    opening: str
    turn: str
    ending: str
    focus: str
    release: bool
    intimate: bool
    quiet: bool
    restless: bool


def short_quote(value: str) -> str:
    value = " ".join(value.strip(" ,.;!?…—–").split()[:12])
    clipped = value[:108]
    if len(value) > len(clipped) and " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped


def interpret(story: str, details: dict) -> StoryArc:
    sentences = [phrase.strip() for phrase in re.split(r"(?<=[.!?…])\s+|\n+", story) if phrase.strip()]
    phrases = [quote for part in sentences for phrase in TURN.split(part) if (quote := short_quote(phrase))]
    if not phrases:
        phrases = [story.strip()[:108]]
    title = ""
    for phrase in phrases:
        candidate = LEAD_IN.sub("", phrase).strip()
        if 3 <= len(candidate.split()) <= 7 and len(candidate) <= 78:
            title = candidate[0].upper() + candidate[1:]
            break
    if not title:
        words = max(phrases[:8], key=lambda phrase: min(len(phrase.split()), 7)).split()[:7]
        title = " ".join(word[:24] for word in words)[:78].strip()
        title = title[:1].upper() + title[1:] if len(title.split()) >= 3 else f"В памяти осталось «{title}»"

    turns = [short_quote(parts[1]) for sentence in sentences if len(parts := TURN.split(sentence, maxsplit=1)) == 2]
    release = list(RELEASE.finditer(story))
    selected = details.get("key_detail", "").strip() or details.get("_closing_detail", "").strip()
    ending = selected or (release[-1].group() if release else phrases[-1])
    ending = short_quote(ending) or ending[:108]
    if not selected and release and ending:
        ending = ending[0].upper() + ending[1:]
    opening = phrases[0]
    if len(phrases) >= 4 and opening.casefold() == title.casefold():
        opening = phrases[1]
    turn = next((part for part in turns if part and part not in (opening, ending)), "")
    if not turn and len(phrases) > 2:
        turn = next((part for part in phrases[1:-1] if part not in (opening, ending)), "")
    mood = details.get("mood", "")
    quiet = bool(QUIET.search(mood or story))
    restless = bool(RESTLESS.search(mood or story))
    return StoryArc(title, opening, turn, ending, "pin" if selected else "release" if release else "excerpt",
                    bool(release), bool(CLOSENESS.search(turn or ending)), quiet, restless)
