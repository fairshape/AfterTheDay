import json
import re
from urllib.parse import urlsplit

import aiohttp

from app.services.song_search import CatalogueUnavailable, Song

ENDPOINT = "https://itunes.apple.com/search"
MAX_RESPONSE = 512 * 1024


def parse_result(raw: dict) -> Song | None:
    if (not isinstance(raw, dict) or raw.get("kind") != "song"
            or type(raw.get("trackId")) is not int or raw.get("isStreamable") is False):
        return None
    fields = [raw.get(key, "") for key in ("trackName", "artistName", "collectionName", "trackViewUrl")]
    if not all(isinstance(value, str) for value in fields):
        return None
    title, artist, album, url = (" ".join(value.split()) for value in fields)
    try:
        target = urlsplit(url)
        valid = (target.scheme == "https" and target.netloc in {"music.apple.com", "itunes.apple.com"}
                 and target.path.startswith("/") and len(url) <= 1500)
    except ValueError:
        return None
    if not valid or not title or not artist:
        return None
    genre = raw.get("primaryGenreName", "")
    year = str(raw.get("releaseDate", ""))[:4]
    return Song(title[:160], artist[:160], album[:160], str(raw["trackId"]), url, "itunes",
                genre[:120] if isinstance(genre, str) else "", year if re.fullmatch(r"[0-9]{4}", year) else "")


class ITunesCatalogue:
    def __init__(self, country: str, timeout: float):
        self.country = country
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def search(self, query: str) -> list[Song]:
        params = {"term": query, "country": self.country, "media": "music", "entity": "song", "limit": 24}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(ENDPOINT, params=params, allow_redirects=False) as response:
                    if response.status != 200:
                        raise CatalogueUnavailable
                    data = bytearray()
                    async for block in response.content.iter_chunked(16384):
                        data.extend(block)
                        if len(data) > MAX_RESPONSE:
                            raise CatalogueUnavailable
            payload = json.loads(data)
            rows = payload["results"]
            return [song for row in rows if (song := parse_result(row))] if isinstance(rows, list) else []
        except (aiohttp.ClientError, OSError, ValueError, KeyError, TypeError) as exc:
            raise CatalogueUnavailable from exc
