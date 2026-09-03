from __future__ import annotations

from .. import endpoints
from ..Core.Request import safe_get
from ..Utils.Text import clean


def _format_playlist_item(item: dict) -> dict:
    more = item.get("more_info") or {}
    return {
        "id": item.get("id"),
        "name": clean(item.get("title") or item.get("listname")),
        "image": (item.get("image") or "").replace("150x150", "500x500"),
        "song_count": more.get("song_count") or item.get("list_count"),
        "follower_count": more.get("follower_count"),
        "language": item.get("language"),
        "play_count": item.get("play_count"),
        "perma_url": item.get("perma_url"),
    }


async def get_charts(*, client=None) -> list[dict]:
    data = await safe_get(client, endpoints.LAUNCH_DATA)
    if not data:
        return []
    items = data.get("charts") or []
    if not isinstance(items, list):
        return []
    return [_format_playlist_item(i) for i in items if isinstance(i, dict)]


async def get_featured_playlists(
    *,
    language: str | list[str] | None = None,
    limit: int = 20,
    client=None,
) -> list[dict]:
    limit = max(1, min(limit, 50))
    data = await safe_get(client, endpoints.LAUNCH_DATA)
    if not data:
        return []

    items = data.get("top_playlists") or []
    if not isinstance(items, list):
        return []

    if language:
        langs = {language.lower()} if isinstance(language, str) else {l.lower() for l in language}
        items = [i for i in items if (i.get("language") or "").lower() in langs]

    return [_format_playlist_item(i) for i in items[:limit] if isinstance(i, dict)]
