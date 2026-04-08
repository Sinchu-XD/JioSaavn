from ..Core.Request import Request
from .. import endpoints
from ..Formatter.Song import format_song
from .Lyrics import get_lyrics


async def get_song(song_id):
    async with Request() as req:
        data = await req.get(endpoints.SONG + song_id)

    if not data:
        return None

    song = data.get(song_id)
    if not song:
        return None

    return await format_song(song, get_lyrics)
