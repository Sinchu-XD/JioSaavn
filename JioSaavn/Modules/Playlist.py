from __future__ import annotations

import re

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Playlist import format_playlist
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def _format_playlist(data: dict) -> dict:
    """Async playlist formatter without lyrics (for URL resolver)."""
    return await format_playlist(data, lyrics_func=None)


async def get_playlist(list_id: str, *, lyrics: bool = False, client=None) -> dict | None:
    if not list_id or not _ID_RE.match(list_id):
        raise ValueError(f"Invalid list_id: {list_id!r}")

    data = await safe_get(client, endpoints.PLAYLIST + list_id)
    if not data:
        return None

    lyrics_func = get_lyrics if lyrics else None
    return await format_playlist(data, lyrics_func)
