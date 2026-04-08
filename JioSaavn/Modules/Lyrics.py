from ..Core.Request import Request
from .. import endpoints


async def get_lyrics(song_id):
    async with Request() as req:
        data = await req.get(endpoints.LYRICS + song_id)

    if not data:
        return None

    return data.get("lyrics")
