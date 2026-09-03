"""Analysis — playlist analysis, recommenders, taste profiles, insights."""
from .Playlist import analyze_playlist, find_duplicates, infer_mood
from .Recommender import recommend_from_history, similar_songs_deep
from .TasteProfile import TasteProfile, build_profile, load_or_build
from .RecommendationEngine import RecommendationEngine
from .Contextual import ContextualRecommender
from .DiscoveryGraph import DiscoveryGraph
from .LyricsAnalysis import LyricsAnalysis
from .Insights import Insights

__all__ = [
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
]
