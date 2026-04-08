from ..Core.Request import Request
from .. import endpoints


async def get_lyrics(song_id, client=None):
    url = endpoints.LYRICS + song_id

    if client:
        data = await client.get(url)
    else:
        async with Request() as req:
            data = await req.get(url)

    if not data:
        return None

    return data.get("lyrics")
