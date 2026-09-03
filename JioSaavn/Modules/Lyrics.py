from __future__ import annotations

import re

from .. import endpoints
from ..Core.Request import safe_get

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


async def get_lyrics(song_id: str, client=None) -> str | None:
    if not song_id or not _ID_RE.match(song_id):
        raise ValueError(f"Invalid song_id: {song_id!r}")

    data = await safe_get(client, endpoints.LYRICS + song_id)
    if not data:
        return None

    return data.get("lyrics")
