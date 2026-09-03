from __future__ import annotations

import asyncio
import re

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def get_radio(
    song_id: str,
    *,
    limit: int = 10,
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    if not song_id or not _ID_RE.match(song_id):
        raise ValueError(f"Invalid song_id: {song_id!r}")

    limit = max(1, min(limit, 25))

    create_url = (
        endpoints.RADIO_CREATE
        + f"&pids={song_id}&k=5&next=1&type=song"
    )
    station_data = await safe_get(client, create_url)
    if not station_data:
        return []

    station_id = station_data.get("stationid")
    if not station_id:
        return []

    songs_url = (
        endpoints.RADIO_SONGS
        + f"&stationid={station_id}&k={limit}&next=1"
    )
    songs_data = await safe_get(client, songs_url)
    if not songs_data:
        return []

    raw_songs: list[dict] = []
    for key, val in songs_data.items():
        if isinstance(val, dict) and val.get("type") == "song":
            raw = val.get("song") or val
            if isinstance(raw, dict):
                raw_songs.append(raw)

    if not raw_songs:
        return []

    sem = asyncio.Semaphore(5)
    lyrics_func = get_lyrics if lyrics else None

    async def process(s: dict) -> dict | None:
        async with sem:
            try:
                return await format_song(s, lyrics_func)
            except Exception:
                return None

    results = await asyncio.gather(*[process(s) for s in raw_songs[:limit]], return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]
