from __future__ import annotations

import asyncio
import re

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def get_song(song_id: str, *, lyrics: bool = False, client=None) -> dict | None:
    if not song_id or not _ID_RE.match(song_id):
        raise ValueError(f"Invalid song_id: {song_id!r}")

    data = await safe_get(client, endpoints.SONG + song_id)
    if not data:
        return None

    song = data.get(song_id)
    if not song:
        return None

    lyrics_func = get_lyrics if lyrics else None
    return await format_song(song, lyrics_func)


async def get_songs(
    song_ids: list[str],
    *,
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    """
    Batch-fetch multiple songs by their JioSaavn IDs in a single API call.

    Parameters
    ----------
    song_ids : list[str]
        Up to 50 JioSaavn song IDs.
    lyrics : bool
        If ``True``, fetch lyrics for each song when available.
    client : JioSaavnClient | None
        Optional shared session client.

    Returns
    -------
    list[dict]
        List of formatted song dicts in the same order as the input IDs
        (missing IDs are silently dropped).

    Example
    -------
    >>> songs = await get_songs(["aRZbUYD7", "4ZSL1xJk", "FpxaLHiB"])
    >>> for s in songs:
    ...     print(s["song"], "—", s["duration"])
    """
    if not song_ids:
        return []

    valid_ids = [sid for sid in song_ids[:50] if sid and _ID_RE.match(sid)]
    if not valid_ids:
        return []

    url = endpoints.SONG + ",".join(valid_ids)

    data = await safe_get(client, url)
    if not data:
        return []

    lyrics_func = get_lyrics if lyrics else None
    sem = asyncio.Semaphore(5)

    async def process(sid: str) -> dict | None:
        raw = data.get(sid)
        if not raw or not isinstance(raw, dict):
            return None
        try:
            return await format_song(raw, lyrics_func)
        except Exception:
            return None

    results = await asyncio.gather(*[process(sid) for sid in valid_ids], return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]
