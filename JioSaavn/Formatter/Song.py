from ..Utils.Crypto import decrypt
from ..Utils.Text import clean


async def format_song(data, lyrics_func=None):
    more = data.get("more_info", {})

    enc = more.get("encrypted_media_url")

    if enc:
        media = decrypt(enc)

        if media and more.get("320kbps") != "true":
            media = media.replace("_320.mp4", "_160.mp4")

        data["media_url"] = media
    else:
        data["media_url"] = None

    artists = more.get("artistMap", {}).get("primary_artists", [])
    data["primary_artists"] = ", ".join([a.get("name", "") for a in artists])

    data["song"] = clean(data.get("title"))
    data["album"] = clean(more.get("album"))
    data["music"] = clean(more.get("music"))

    if data.get("image"):
        data["image"] = data["image"].replace("150x150", "500x500")

    if lyrics_func and more.get("has_lyrics") == "true":
        data["lyrics"] = await lyrics_func(data.get("id"))

    return data
