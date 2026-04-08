import urllib.parse
from ..Core.Request import Request
from .. import endpoints
from .Song import get_song


async def search(query, full=False):
    query = urllib.parse.quote(query)

    async with Request() as req:
        data = await req.get(endpoints.SEARCH + query)

    if not data:
        return []

    songs = data.get("results") or data.get("songs", {}).get("data", [])

    if not full:
        return songs

    return [
        await get_song(s.get("id"))
        for s in songs
        if s.get("id")
    ]
