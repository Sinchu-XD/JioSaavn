from __future__ import annotations

import asyncio
import re
import urllib.parse

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def get_suggestions(
    song_id: str,
    *,
    limit: int = 10,
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    if not song_id or not _ID_RE.match(song_id):
        raise ValueError(f"Invalid song_id: {song_id!r}")

    limit = max(1, min(limit, 50))

    # ── Attempt 1: native recommendation endpoint ──────────────────────────
    url = endpoints.SUGGESTIONS + song_id + f"&n={limit}"
    data = await safe_get(client, url)

    if data:
        songs_raw = data.get(song_id) or []
        if isinstance(songs_raw, list) and songs_raw:
            lyrics_func = get_lyrics if lyrics else None
            return [
                await format_song(s, lyrics_func)
                for s in songs_raw[:limit]
                if isinstance(s, dict)
            ]

    # ── Attempt 2: get song details → search by primary artist ────────────
    song_data = await safe_get(client, endpoints.SONG + song_id)
    if not song_data:
        return []

    raw = song_data.get(song_id) or {}
    more = raw.get("more_info") or {}
    artist_map = more.get("artistMap") or {}
    primary = artist_map.get("primary_artists") or []
    artist_name = primary[0].get("name") if primary and isinstance(primary[0], dict) else None

    if not artist_name:
        return []

    encoded = urllib.parse.quote(artist_name.strip())
    search_url = endpoints.SEARCH + encoded
    search_data = await safe_get(client, search_url)
    if not search_data:
        return []

    candidates = search_data.get("results") or search_data.get("songs", {}).get("data", [])
    if not isinstance(candidates, list):
        return []

    # exclude the input song
    candidates = [s for s in candidates if s.get("id") != song_id][:limit]

    sem = asyncio.Semaphore(5)
    lyrics_func = get_lyrics if lyrics else None

    async def process(s: dict) -> dict | None:
        async with sem:
            try:
                return await format_song(s, lyrics_func)
            except Exception:
                return None

    results = await asyncio.gather(*[process(s) for s in candidates], return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]
