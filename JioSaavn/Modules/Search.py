import urllib.parse
from ..Core.Request import Request
from .. import endpoints
from .Song import get_song


async def search(query, full=False, client=None):
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

    if not full:
        return songs

    return [
        await get_song(s.get("id"), client=client)
        for s in songs
        if s.get("id")
    ]
