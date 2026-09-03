"""
JioSaavn
========

Fast, fully-async Python wrapper for the JioSaavn API.

Quick start
-----------

.. code-block:: python

    import asyncio
    from JioSaavn import search, get_song, get_artist, get_trending

    async def main():
        # Search songs
        songs = await search("Arijit Singh", limit=5)
        for s in songs:
            print(s["song"], "—", s["primary_artists"])

        # Batch-fetch multiple songs
        tracks = await get_songs([s["id"] for s in songs])

        # Radio station seeded from first song
        radio = await get_radio(songs[0]["id"], limit=10)

        # All homepage modules at once
        modules = await get_modules(language="hindi", limit=5)
        for t in modules["trending"]:
            print(t["title"])

        # Resolve a JioSaavn share URL
        song = await get_song_by_url("https://www.jiosaavn.com/song/tum-hi-ho/aRZbUYD7")

        # All categories in one call
        results = await search_all("Pritam", limit=3)

    asyncio.run(main())
"""

from .Modules.Search import (
    search,
    search_songs,
    search_albums,
    search_artists,
    search_playlists,
    search_all,
)
from .Modules.Song import get_song, get_songs
from .Modules.Album import get_album
from .Modules.Playlist import get_playlist
from .Modules.Lyrics import get_lyrics
from .Modules.Artist import (
    get_artist,
    get_artist_top_songs,
    get_artist_top_albums,
)
from .Modules.Trending import get_trending, get_new_releases, get_top_searches, get_modules
from .Modules.Charts import get_charts, get_featured_playlists
from .Modules.Suggestions import get_suggestions
from .Modules.Radio import get_radio
from .Modules.Resolve import get_song_by_url, get_album_by_url, get_playlist_by_url
from .Core.Client import JioSaavnClient

from .Modules.SmartQueue import SmartQueue
from .Utils.Crossfade import crossfade_plan

from .Analysis.Playlist import analyze_playlist, find_duplicates, infer_mood
from .Analysis.Recommender import recommend_from_history, similar_songs_deep
from .Analysis.TasteProfile import TasteProfile, build_profile, load_or_build
from .Analysis.RecommendationEngine import RecommendationEngine
from .Analysis.Contextual import ContextualRecommender
from .Analysis.DiscoveryGraph import DiscoveryGraph
from .Analysis.LyricsAnalysis import LyricsAnalysis
from .Analysis.Insights import Insights

from .Modules.Sync import sync_spotify_playlist, sync_youtube_playlist
from .Modules.Backup import backup_library, restore_library

from .Modules.AdvSearch import fuzzy_search, search_by_lyrics, search_filters

from .Modules.DownloadPro import DownloadManager, download_with_lyrics

from .Modules.Discovery import daily_mix, time_machine, regional_charts, artist_radio

from .Modules.Social import get_song_credits, get_release_calendar, compare_artists

from .Modules.Webhooks import WebhookNotifier

__version__ = "2026.9.3"
__author__ = "Abhi Singh"
__license__ = "MIT"

__all__ = [
    # ── Search ──────────────────────────────────────────────────
    "search",
    "search_songs",
    "search_albums",
    "search_artists",
    "search_playlists",
    "search_all",
    # ── Songs ───────────────────────────────────────────────────
    "get_song",
    "get_songs",
    "get_lyrics",
    "get_suggestions",
    "get_radio",
    # ── URL Resolvers ───────────────────────────────────────────
    "get_song_by_url",
    "get_album_by_url",
    "get_playlist_by_url",
    # ── Albums ──────────────────────────────────────────────────
    "get_album",
    # ── Playlists ───────────────────────────────────────────────
    "get_playlist",
    # ── Artists ─────────────────────────────────────────────────
    "get_artist",
    "get_artist_top_songs",
    "get_artist_top_albums",
    # ── Discovery ───────────────────────────────────────────────
    "get_trending",
    "get_new_releases",
    "get_top_searches",
    "get_charts",
    "get_featured_playlists",
    "get_modules",
    # ── Session client ──────────────────────────────────────────
    "JioSaavnClient",
    # ── Smart playback ──────────────────────────────────────────
    "SmartQueue",
    "crossfade_plan",
    # ── Analysis ────────────────────────────────────────────────
    "analyze_playlist",
    "find_duplicates",
    "infer_mood",
    "recommend_from_history",
    "similar_songs_deep",
    "TasteProfile",
    "build_profile",
    "load_or_build",
    "RecommendationEngine",
    "ContextualRecommender",
    "DiscoveryGraph",
    "LyricsAnalysis",
    "Insights",
    # ── Sync / backup ───────────────────────────────────────────
    "sync_spotify_playlist",
    "sync_youtube_playlist",
    "backup_library",
    "restore_library",
    # ── Advanced search ─────────────────────────────────────────
    "fuzzy_search",
    "search_by_lyrics",
    "search_filters",
    # ── Download Pro ────────────────────────────────────────────
    "DownloadManager",
    "download_with_lyrics",
    # ── Discovery features ──────────────────────────────────────
    "daily_mix",
    "time_machine",
    "regional_charts",
    "artist_radio",
    # ── Social / metadata ───────────────────────────────────────
    "get_song_credits",
    "get_release_calendar",
    "compare_artists",
    # ── Webhooks ────────────────────────────────────────────────
    "WebhookNotifier",
]
