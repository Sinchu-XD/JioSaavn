from __future__ import annotations

import asyncio
import urllib.parse

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Song import format_song
from ..Utils.Text import clean
from .Lyrics import get_lyrics


async def search(
    query: str,
    limit: int = 10,
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    limit = max(1, min(limit, 50))
    encoded = urllib.parse.quote(query.strip())
    url = endpoints.SEARCH + encoded
    data = await safe_get(client, url)
    if not data:
        return []

    songs = data.get("results") or data.get("songs", {}).get("data", [])
    if not isinstance(songs, list):
        return []
    songs = songs[:limit]

    sem = asyncio.Semaphore(5)

    async def process(song: dict) -> dict | None:
        try:
            async with sem:
                if not song.get("id"):
                    return None
                return await format_song(song, get_lyrics if lyrics else None)
        except Exception:
            return None

    results = await asyncio.gather(*[process(s) for s in songs], return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]


async def search_songs(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
    lyrics: bool = False,
    client=None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    limit = max(1, min(limit, 50))
    encoded = urllib.parse.quote(query.strip())
    url = endpoints.SEARCH_SONGS + encoded + f"&p={page}&n={limit}"
    data = await safe_get(client, url)
    if not data:
        return []

    songs = data.get("results") or data.get("songs", {}).get("data", [])
    if not isinstance(songs, list):
        return []

    sem = asyncio.Semaphore(5)

    async def process(song: dict) -> dict | None:
        try:
            async with sem:
                return await format_song(song, get_lyrics if lyrics else None)
        except Exception:
            return None

    results = await asyncio.gather(*[process(s) for s in songs[:limit]], return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]


async def search_albums(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
    client=None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    limit = max(1, min(limit, 50))
    encoded = urllib.parse.quote(query.strip())
    url = endpoints.SEARCH_ALBUMS + encoded + f"&p={page}&n={limit}"
    data = await safe_get(client, url)
    if not data:
        return []

    albums = data.get("results") or data.get("albums", {}).get("data", [])
    if not isinstance(albums, list):
        return []

    result = []
    for a in albums[:limit]:
        if not isinstance(a, dict):
            continue
        result.append({
            "id": a.get("id") or a.get("albumid"),
            "name": clean(a.get("title") or a.get("name")),
            "year": a.get("year"),
            "image": (a.get("image") or "").replace("150x150", "500x500"),
            "primary_artists": clean(a.get("primary_artists") or a.get("music") or ""),
            "language": a.get("language"),
            "song_count": a.get("song_count") or a.get("num_song"),
        })
    return result


async def search_artists(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
    client=None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    limit = max(1, min(limit, 50))
    encoded = urllib.parse.quote(query.strip())
    url = endpoints.SEARCH_ARTISTS + encoded + f"&p={page}&n={limit}"
    data = await safe_get(client, url)
    if not data:
        return []

    artists = data.get("results") or data.get("artists", {}).get("data", [])
    if not isinstance(artists, list):
        return []

    result = []
    for a in artists[:limit]:
        if not isinstance(a, dict):
            continue
        result.append({
            "id": a.get("id") or a.get("artistId"),
            "name": clean(a.get("name")),
            "image": (a.get("image") or "").replace("150x150", "500x500"),
            "dominant_language": a.get("dominantLanguage"),
            "dominant_type": a.get("dominantType"),
            "role": a.get("role"),
            "follower_count": a.get("followerCount") or a.get("follower_count"),
        })
    return result


async def search_playlists(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
    client=None,
) -> list[dict]:
    if not query or not query.strip():
        return []

    limit = max(1, min(limit, 50))
    encoded = urllib.parse.quote(query.strip())
    url = endpoints.SEARCH_PLAYLISTS + encoded + f"&p={page}&n={limit}"
    data = await safe_get(client, url)
    if not data:
        return []

    playlists = data.get("results") or data.get("playlists", {}).get("data", [])
    if not isinstance(playlists, list):
        return []

    result = []
    for p in playlists[:limit]:
        if not isinstance(p, dict):
            continue
        result.append({
            "id": p.get("id") or p.get("listid"),
            "name": clean(p.get("title") or p.get("listname")),
            "image": (p.get("image") or "").replace("150x150", "500x500"),
            "song_count": p.get("song_count") or p.get("listCount"),
            "follower_count": p.get("follower_count"),
            "language": p.get("language"),
        })
    return result


async def search_all(
    query: str,
    *,
    limit: int = 5,
    client=None,
) -> dict:
    if not query or not query.strip():
        return {"songs": [], "albums": [], "artists": [], "playlists": []}

    limit = max(1, min(limit, 20))

    songs, albums, artists, playlists = await asyncio.gather(
        search_songs(query, limit=limit, client=client),
        search_albums(query, limit=limit, client=client),
        search_artists(query, limit=limit, client=client),
        search_playlists(query, limit=limit, client=client),
    )

    return {
        "songs": songs,
        "albums": albums,
        "artists": artists,
        "playlists": playlists,
    }
