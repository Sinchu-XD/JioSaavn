from __future__ import annotations

import re

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Artist import format_artist
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics

_ID_RE = re.compile(r"^[0-9]{1,20}$")


async def get_artist(
    artist_id: str,
    *,
    n_song: int = 10,
    n_album: int = 10,
    lyrics: bool = False,
    client=None,
) -> dict | None:
    if not artist_id or not str(artist_id).strip():
        raise ValueError("artist_id must not be empty")

    artist_id = str(artist_id).strip()
    if not _ID_RE.match(artist_id):
        raise ValueError(
            f"artist_id must be a numeric ID (e.g. '459320'), got: {artist_id!r}. "
            "Use search_artists() to find the numeric ID for an artist name."
        )

    url = (
        endpoints.ARTIST_BY_ID
        + artist_id
        + f"&n_song={n_song}&n_album={n_album}&page=0"
    )

    data = await safe_get(client, url)
    if not data or "error" in data:
        return None

    lyrics_func = get_lyrics if lyrics else None
    return await format_artist(data, lyrics_func)


async def get_artist_top_songs(
    artist_id: str,
    *,
    page: int = 1,
    category: str = "popularity",
    sort_order: str = "desc",
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    artist_id = str(artist_id).strip()
    if not _ID_RE.match(artist_id):
        raise ValueError(f"artist_id must be a numeric ID, got: {artist_id!r}")

    url = (
        endpoints.ARTIST_TOP_SONGS
        + artist_id
        + f"&page={page}&category={category}&sort_order={sort_order}"
    )

    data = await safe_get(client, url)
    if not data or "error" in data:
        return []

    songs_raw = (data.get("topSongs") or {}).get("songs") or data.get("songs") or data.get("data") or []
    lyrics_func = get_lyrics if lyrics else None

    results = []
    for s in songs_raw:
        if isinstance(s, dict):
            results.append(await format_song(s, lyrics_func))
    return results


async def get_artist_top_albums(
    artist_id: str,
    *,
    page: int = 1,
    category: str = "latest",
    sort_order: str = "desc",
    client=None,
) -> list[dict]:
    artist_id = str(artist_id).strip()
    if not _ID_RE.match(artist_id):
        raise ValueError(f"artist_id must be a numeric ID, got: {artist_id!r}")

    url = (
        endpoints.ARTIST_TOP_ALBUMS
        + artist_id
        + f"&page={page}&category={category}&sort_order={sort_order}"
    )

    data = await safe_get(client, url)
    if not data or "error" in data:
        return []

    from ..Formatter.Artist import _format_album_brief

    albums_raw = (data.get("topAlbums") or {}).get("albums") or data.get("albums") or data.get("data") or []
    return [_format_album_brief(a) for a in albums_raw if isinstance(a, dict)]
