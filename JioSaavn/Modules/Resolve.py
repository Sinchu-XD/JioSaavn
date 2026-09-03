from __future__ import annotations

import re
import urllib.parse

from .. import endpoints
from ..Core.Request import safe_get
from ..Formatter.Song import format_song
from ..Utils.Text import clean
from .Lyrics import get_lyrics

_TOKEN_RE = re.compile(r"/([A-Za-z0-9_-]{6,20})(?:/|$|\?)")


def _extract_token(url: str) -> str | None:
    """Pull the encoded token from the last meaningful path segment."""
    path = urllib.parse.urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    token = parts[-1]
    if re.fullmatch(r"[A-Za-z0-9_-]{4,30}", token):
        return token
    return None


async def _resolve(url: str, kind: str, client=None) -> dict | None:
    token = _extract_token(url)
    if not token:
        raise ValueError(f"Cannot extract token from URL: {url!r}")
    api_url = endpoints.RESOLVE + f"&token={token}&type={kind}"
    return await safe_get(client, api_url)


async def get_song_by_url(
    url: str,
    *,
    lyrics: bool = False,
    client=None,
) -> dict | None:
    """
    Fetch full song details from a JioSaavn share URL.

    Parameters
    ----------
    url : str
        A JioSaavn song URL, e.g.
        ``"https://www.jiosaavn.com/song/tum-hi-ho/aRZbUYD7"``.
    lyrics : bool
        Also fetch lyrics if the song has them.
    client : JioSaavnClient | None
        Optional shared session client.

    Returns
    -------
    dict | None
        Formatted song dict (same shape as :func:`get_song`), or ``None``.

    Example
    -------
    >>> song = await get_song_by_url("https://www.jiosaavn.com/song/tum-hi-ho/aRZbUYD7")
    >>> print(song["song"], song["primary_artists"])
    """
    data = await _resolve(url, "song", client=client)
    if not data:
        return None
    songs = data.get("songs") or []
    if not songs or not isinstance(songs, list):
        return None
    lyrics_func = get_lyrics if lyrics else None
    return await format_song(songs[0], lyrics_func)


async def get_album_by_url(url: str, *, client=None) -> dict | None:
    """
    Fetch full album details from a JioSaavn share URL.

    Parameters
    ----------
    url : str
        A JioSaavn album URL, e.g.
        ``"https://www.jiosaavn.com/album/rockstar/AbCdEf12"``.
    client : JioSaavnClient | None
        Optional shared session client.

    Returns
    -------
    dict | None
        Formatted album dict (same shape as :func:`get_album`), or ``None``.

    Example
    -------
    >>> album = await get_album_by_url("https://www.jiosaavn.com/album/rockstar/AbCdEf12")
    >>> print(album["name"], album["year"])
    """
    from .Album import _format_album
    data = await _resolve(url, "album", client=client)
    if not data:
        return None
    return _format_album(data)


async def get_playlist_by_url(url: str, *, client=None) -> dict | None:
    """
    Fetch full playlist details from a JioSaavn share URL.

    Parameters
    ----------
    url : str
        A JioSaavn playlist/featured URL, e.g.
        ``"https://www.jiosaavn.com/featured/top-50-songs/AbCdEf12"``.
    client : JioSaavnClient | None
        Optional shared session client.

    Returns
    -------
    dict | None
        Formatted playlist dict (same shape as :func:`get_playlist`), or ``None``.

    Example
    -------
    >>> pl = await get_playlist_by_url("https://www.jiosaavn.com/featured/top-50/AbCdEf12")
    >>> print(pl["listname"], pl["song_count"])
    """
    from .Playlist import _format_playlist
    data = await _resolve(url, "playlist", client=client)
    if not data:
        return None
    return await _format_playlist(data)
