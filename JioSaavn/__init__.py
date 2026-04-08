from .Modules.Search import search
from .Modules.Song import get_song
from .Modules.Album import get_album
from .Modules.Playlist import get_playlist
from .Modules.Lyrics import get_lyrics

__all__ = [
    "search",
    "get_song",
    "get_album",
    "get_playlist",
    "get_lyrics"
]
