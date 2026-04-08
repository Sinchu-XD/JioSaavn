from ..Utils.Text import clean
from .Song import format_song


async def format_album(data, lyrics_func=None):
    data["image"] = data.get("image", "").replace("150x150", "500x500")
    data["name"] = clean(data.get("name"))
    data["primary_artists"] = clean(data.get("primary_artists"))
    data["title"] = clean(data.get("title"))

    songs = data.get("songs", [])

    formatted = []
    for s in songs:
        formatted.append(await format_song(s, lyrics_func))

    data["songs"] = formatted

    return data
