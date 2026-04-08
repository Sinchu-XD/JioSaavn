from ..Core.Request import Request
from .. import endpoints
from ..Formatter.Album import format_album
from .Lyrics import get_lyrics


async def get_album(album_id):
    async with Request() as req:
        data = await req.get(endpoints.ALBUM + album_id)

    if not data:
        return None

    return await format_album(data, get_lyrics)
