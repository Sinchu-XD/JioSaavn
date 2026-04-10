import urllib.parse
import asyncio

from ..Core.Request import Request
from .. import endpoints
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics


async def search(query, limit=10, lyrics=False, client=None):
    query = urllib.parse.quote(query)
    url = endpoints.SEARCH + query

    if client:
        data = await client.get(url)
    else:
        async with Request() as req:
            data = await req.get(url)

    if not data:
        return []

    songs = data.get("results") or data.get("songs", {}).get("data", [])
    songs = songs[:limit]

    async def process(song):
        return await format_song(
            song,
            get_lyrics if lyrics else None
        )

    return await asyncio.gather(*[
        process(s) for s in songs if s.get("id")
    ])
