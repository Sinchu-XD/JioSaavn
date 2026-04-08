from ..Utils.Text import clean
from .Song import format_song


async def format_playlist(data, lyrics_func=None):
    data["firstname"] = clean(data.get("firstname"))
    data["listname"] = clean(data.get("listname"))

    songs = data.get("songs", [])

    formatted = []
    for s in songs:
        formatted.append(await format_song(s, lyrics_func))

    data["songs"] = formatted

    return data
