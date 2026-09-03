from __future__ import annotations

import re

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Album import format_album
from ..Utils.Text import clean
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _format_album(data: dict) -> dict:
    """Synchronous lightweight album formatter (for URL resolver)."""
    return {
        "id": data.get("id") or data.get("albumid"),
        "name": clean(data.get("name") or data.get("title")),
        "primary_artists": clean(data.get("primary_artists")),
        "image": (data.get("image") or "").replace("150x150", "500x500"),
        "year": data.get("year"),
        "release_date": data.get("release_date"),
        "language": data.get("language"),
        "label": data.get("label_name") or data.get("label"),
        "song_count": data.get("song_count"),
    }


async def get_album(album_id: str, *, lyrics: bool = False, client=None) -> dict | None:
    if not album_id or not _ID_RE.match(album_id):
        raise ValueError(f"Invalid album_id: {album_id!r}")

    data = await safe_get(client, endpoints.ALBUM + album_id)
    if not data:
        return None

    lyrics_func = get_lyrics if lyrics else None
    return await format_album(data, lyrics_func)
