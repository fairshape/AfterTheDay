from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
import re
from typing import Protocol
from uuid import uuid4

class CatalogueUnavailable(Exception):
    pass


QUERY_TTL = 180
CHOICE_TTL = 600
CACHE_LIMIT = 128


def tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", value.casefold()))


@dataclass(frozen=True)
class Song:
    title: str
    artist: str
    album: str
    track_id: str
    url: str
    provider: str

    def attachment(self) -> dict:
        return {"kind": "link", "provider": self.provider, "track_id": self.track_id,
                "title": self.title, "artist": self.artist, "album": self.album, "url": self.url}


class Catalogue(Protocol):
    async def search(self, query: str) -> list[Song]: ...


class SongSearch:
    def __init__(self, provider: Catalogue):
        self.provider = provider
        self.cache = OrderedDict()
        self.choices = OrderedDict()

    @staticmethod
    def remember(cache, key, value) -> None:
        cache[key] = value
        cache.move_to_end(key)
        if len(cache) > CACHE_LIMIT:
            cache.popitem(last=False)

    async def find(self, query: str) -> tuple[Song, ...]:
        query = " ".join(query.split())
        key = query.casefold()
        cached = self.cache.get(key)
        if cached and cached[0] > monotonic():
            self.cache.move_to_end(key)
            return cached[1]
        matches = await self.provider.search(query)
        query_tokens = tokens(query)
        words = set(query_tokens)

        def rank(song):
            sequence = tokens(song.title)
            title, artist = set(sequence), set(tokens(song.artist))
            exact_title = any(query_tokens[index:index+len(sequence)] == sequence
                              for index in range(len(query_tokens)-len(sequence)+1))
            artist_match = bool((words - title) & artist)
            return (exact_title and artist_match, exact_title, words <= title | artist,
                    len(words & title) + len(words & artist), -len(title - words))

        results = []
        seen = set()
        ids = set()
        for song in sorted(matches, key=rank, reverse=True):
            variant = (song.title.casefold(), song.artist.casefold(), song.album.casefold())
            if song.track_id not in ids and variant not in seen:
                results.append(song)
                seen.add(variant)
                ids.add(song.track_id)
            if len(results) == 5:
                break
        selection = tuple(results)
        self.remember(self.cache, key, (monotonic() + QUERY_TTL, selection))
        return selection

    def offer(self, day, songs: tuple[Song, ...]) -> str:
        token = uuid4().hex[:16]
        self.remember(self.choices, day.owner_id, (monotonic() + CHOICE_TTL, day.id, day.revision, token, songs))
        return token

    def choose(self, day, token: str, index: int) -> Song | None:
        record = self.choices.get(day.owner_id)
        if record is None:
            return None
        expiry, day_id, revision, expected, songs = record
        if (expiry > monotonic() and day_id == day.id and revision == day.revision
                and token == expected and 0 <= index < len(songs)):
            return songs[index]
        return None
