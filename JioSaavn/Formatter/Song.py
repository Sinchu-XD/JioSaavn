from ..Utils.Crypto import decrypt
from ..Utils.Text import clean


async def format_song(data, lyrics_func=None):
    more = data.get("more_info", {})

    data["id"] = data.get("id")


    data["song"] = clean(data.get("title"))


    data["album"] = clean(more.get("album"))
    data["music"] = clean(more.get("music"))


    artists = more.get("artistMap", {}).get("primary_artists", [])
    data["primary_artists"] = ", ".join([a.get("name", "") for a in artists])

    
    if data.get("image"):
        data["image"] = data["image"].replace("150x150", "500x500")


    duration = data.get("duration")
    if duration:
        try:
            duration = int(duration)
            mins = duration // 60
            secs = duration % 60
            data["duration"] = f"{mins}:{secs:02d}"
        except:
            data["duration"] = None
    else:
        data["duration"] = None


    views = more.get("play_count") or more.get("view_count")
    data["views"] = views


    enc = more.get("encrypted_media_url")
    if enc:
        media = decrypt(enc)

        if media and more.get("320kbps") != "true":
            media = media.replace("_320.mp4", "_160.mp4")

        data["media_url"] = media
    else:
        data["media_url"] = None

    
    if lyrics_func and more.get("has_lyrics") == "true":
        data["lyrics"] = await lyrics_func(data.get("id"))
    else:
        data["lyrics"] = None

    return data
