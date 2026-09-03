"""LyricsAnalysis — sentiment, themes, key phrases from lyrics.

Pure-Python keyword-based analysis with zero external dependencies.
Uses the same lyric-fetching mechanism as ``JioSaavn.Modules.Lyrics``.

Usage::

    from JioSaavn.Analysis.LyricsAnalysis import LyricsAnalysis
    analysis = await LyricsAnalysis.from_song(client, song_id)
    print(analysis.sentiment())
    print(analysis.themes())
    print(analysis.key_phrases())
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

# ── Sentiment lexicons ────────────────────────────────────────────────
_POSITIVE_WORDS = {
    "love", "happy", "joy", "beautiful", "wonderful", "amazing", "great",
    "good", "best", "sweet", "smile", "laugh", "peace", "hope", "dream",
    "sunshine", "heaven", "blessed", "forever", "together", "dil", "pyaar",
    "khushi", "mohabbat", "zindagi", "chaand", "jaan", "tum", "mera",
    "shine", "light", "bright", "fly", "free", "strong", "brave", "kind",
    "warm", "embrace", "kiss", "heart", "soul", "divine", "bliss", "bloom",
    "dance", "sing", "music", "magic", "miracle", "paradise", "angel",
}

_NEGATIVE_WORDS = {
    "sad", "pain", "tears", "heartbreak", "lost", "alone", "dark", "cry",
    "broken", "fear", "hate", "angry", "mad", "hurt", "suffer", "death",
    "goodbye", "leave", "gone", "miss", "regret", "shame", "guilt", "war",
    "dukh", "dard", "aansu", "tanhaai", "judai", "bekarar", "jala",
    "agony", "despair", "hopeless", "worthless", "cursed", "doom", "tear",
    "fight", "kill", "die", "destroy", "shatter", "wound", "ache", "bleed",
}

# ── Theme lexicons ────────────────────────────────────────────────────
_THEMES = {
    "love": {
        "pyaar", "mohabbat", "jaan", "dil", "heart", "love", "beloved",
        "romance", "together", "embrace", "kiss", "darling", "beautiful",
    },
    "devotion": {
        "bhagwan", "ishwar", "allah", "god", "lord", "prayer", "devotional",
        "aarti", "bhajan", "shirdi", "ram", "krishna", "shiva", "divine",
        "blessed", "pray", "faith", "temple", "mosque", "church",
    },
    "party": {
        "party", "dance", "groove", "beat", "dj", "nightclub", "rave",
        "masti", "hangover", "dj", "remix", "pump", "energy",
    },
    "nature": {
        "rain", "barish", "baarish", "monsoon", "river", "mountain",
        "ocean", "sea", "sky", "cloud", "storm", "wind", "tree", "flower",
        "garden", "meadow", "sunset", "sunrise", "moon", "star",
    },
    "heartbreak": {
        "heartbreak", "breakup", "broken", "tears", "cry", "alone",
        "dukh", "dard", "judai", "tanhaai", "farewell", "goodbye", "lost",
    },
    "friendship": {
        "friend", "dosti", "yaar", "partner", "together", "ride", "die",
        "gang", "crew", "brother", "sister", "buddy", "pal",
    },
    "rebellion": {
        "fight", "rebel", "revolution", "freedom", "chains", "escape",
        "defy", "resist", "protest", "stand", "voice", "change",
    },
    "nostalgia": {
        "remember", "memory", "past", "childhood", "old", "yesterday",
        "yaadein", "yaade", "purana", "vintage", "throwback",
    },
    "spiritual": {
        "soul", "meditation", "chakra", "universe", "consciousness",
        "enlightenment", "awakening", "peace", "zen", "mindfulness",
    },
}

# stopwords — words we ignore for key-phrase extraction
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "could", "should", "may", "might", "must", "can", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "but", "and",
    "or", "if", "while", "about", "against", "up", "down", "this", "that",
    "these", "those", "i", "me", "my", "we", "our", "you", "your", "he",
    "she", "it", "they", "them", "his", "her", "its", "their", "what",
    "which", "who", "whom", "ye", "o", "oh", "ha", "ho", "la", "na",
    "tu", "teri", "tum", "tere", "tujhe", "mujhe", "main", "mein", "ka",
    "ki", "ke", "ko", "se", "par", "aur", "nahi", "hai", "hain", "tha",
    "thi", "thi", "bhi", "toh", "yeh", "woh", "kya", "kaise", "kabhi",
    "ab", "phir", "ya", "jab", "tak", "pa", "ra", "li", "ne", "un", "unke",
    "us", "uske", "jiske", "jab", "jahan", "thaa", "thii", "thaa",
    "sa", "si", "hue", "hua", "thi", "the", "diya", "kiya", "karo",
}


class LyricsAnalysis:
    """Analyze a song's lyrics for sentiment, themes, and key phrases."""

    def __init__(self, song_id: str, lyrics: str | None, song_meta: dict):
        self.song_id = song_id
        self.lyrics = lyrics or ""
        self.song_meta = song_meta

    # ── factory ──────────────────────────────────────────────────────
    @staticmethod
    async def from_song(client: Any, song_id: str) -> "LyricsAnalysis | None":
        """Create a ``LyricsAnalysis`` from a song ID by fetching lyrics."""
        try:
            from ..Modules.Lyrics import get_lyrics
            from ..Formatter.Song import format_song
            from ..Core.Request import safe_get
            from .. import endpoints

            raw = await safe_get(client, endpoints.SONG + song_id)
            if not raw:
                return None
            song_data = raw.get(song_id) or raw
            lyrics = await get_lyrics(song_id, client=client)
            return LyricsAnalysis(song_id, lyrics, song_data)
        except Exception:
            return None

    # ── sentiment ────────────────────────────────────────────────────
    def sentiment(self) -> dict[str, float]:
        """Return ``{"positive": x, "negative": y, "compound": z}``.

        Values are 0.0–1.0 for positive/negative; compound is -1.0..1.0.
        """
        words = self._tokenize()
        if not words:
            return {"positive": 0.0, "negative": 0.0, "compound": 0.0}

        pos_count = sum(1 for w in words if w in _POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in _NEGATIVE_WORDS)
        total = len(words)

        pos = round(pos_count / total, 4)
        neg = round(neg_count / total, 4)
        compound = round((pos - neg) * 2, 4)  # -2..2 → -1..1 clamped

        return {
            "positive": min(pos, 1.0),
            "negative": min(neg, 1.0),
            "compound": max(-1.0, min(compound, 1.0)),
        }

    # ── themes ───────────────────────────────────────────────────────
    def themes(self, top_k: int = 5) -> list[tuple[str, float]]:
        """Detect thematic categories in the lyrics."""
        words = set(self._tokenize())
        scored: list[tuple[str, float]] = []
        for theme, keywords in _THEMES.items():
            overlap = len(words & keywords)
            if overlap:
                scored.append((theme, round(overlap / len(keywords), 4)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ── key phrases ──────────────────────────────────────────────────
    def key_phrases(self, top_k: int = 8) -> list[str]:
        """Extract meaningful repeated word pairs and high-frequency nouns."""
        words = [w for w in self._tokenize() if w not in _STOPWORDS and len(w) > 2]
        if not words:
            return []

        # word frequency
        freq = Counter(words)

        # bigrams
        bigrams: Counter = Counter()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            bigrams[bigram] += 1

        # combine: weight bigrams higher
        combined: Counter = Counter()
        for w, c in freq.most_common(20):
            combined[w] = c * 1.0
        for bg, c in bigrams.most_common(15):
            combined[bg] = c * 1.5

        return [p for p, _ in combined.most_common(top_k)]

    # ── summary ──────────────────────────────────────────────────────
    def summary(self) -> dict[str, Any]:
        """Full analysis summary."""
        sent = self.sentiment()
        theme_list = self.themes()
        phrases = self.key_phrases()

        label = "neutral"
        if sent["compound"] >= 0.3:
            label = "positive"
        elif sent["compound"] <= -0.3:
            label = "negative"

        return {
            "song_id": self.song_id,
            "sentiment": sent,
            "sentiment_label": label,
            "themes": theme_list,
            "key_phrases": phrases,
            "lyrics_excerpt": self.lyrics[:300] if self.lyrics else "",
        }

    # ── internals ────────────────────────────────────────────────────
    def _tokenize(self) -> list[str]:
        """Lowercase word list from lyrics."""
        text = self.lyrics.lower()
        # strip common lyric annotations like [intro], (verse), etc.
        text = re.sub(r"\[.*?\]", " ", text)
        text = re.sub(r"\(.*?\)", " ", text)
        text = re.sub(r"[^a-zA-Zऀ-ॿ઀-૿\s]", " ", text)
        return text.split()


__all__ = ["LyricsAnalysis"]
