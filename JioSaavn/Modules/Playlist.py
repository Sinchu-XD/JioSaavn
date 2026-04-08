from ..Core.Request import Request
from .. import endpoints
from ..Formatter.Playlist import format_playlist
from .Lyrics import get_lyrics


async def get_playlist(list_id):
    async with Request() as req:
        data = await req.get(endpoints.PLAYLIST + list_id)

    if not data:
        return None

    return await format_playlist(data, get_lyrics)
