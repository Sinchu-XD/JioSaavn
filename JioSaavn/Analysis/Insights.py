"""Insights — listening analytics and trend analysis.

Computes insights from a list of songs (e.g. a user's downloaded library):

* Genre / language / artist distribution
* Temporal listening trends (by year, decade)
* Explicit-content ratio
* Mood profile summary
* Top charts (songs, artists, albums)
* Growth trajectory (when songs were added, listening velocity)

Usage::

    from JioSaavn.Analysis.Insights import Insights
    insights = Insights.from_songs(songs)
    insights.summary()
    insights.genre_chart()
    insights.mood_profile()
    insights.time_distribution()
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from collections import Counter, defaultdict
from typing import Any


_DB_PATH = "saavn_downloads.db"


class Insights:
    """Analytics engine over a song collection.

    Parameters
    ----------
    songs:
        List of song dicts (from downloads, playlists, search results, etc.).
    profile_id:
        Optional ID for persisted insights.
    """

    def __init__(self, songs: list[dict], profile_id: str = "default"):
        self.songs = songs or []
        self.profile_id = profile_id

    # ── factory ──────────────────────────────────────────────────────
    @staticmethod
    def from_songs(songs: list[dict], profile_id: str = "default") -> "Insights":
        return Insights(songs, profile_id)

    # ── core summaries ───────────────────────────────────────────────
    def summary(self) -> dict[str, Any]:
        """Full analytics summary."""
        return {
            "total_songs": self.total_songs(),
            "total_duration_minutes": round(self.total_duration() / 60, 1),
            "unique_languages": self.unique_count("language"),
            "unique_artists": self.unique_count("primary_artists"),
            "explicit_ratio": self.explicit_ratio(),
            "avg_duration_seconds": self.avg_duration(),
            "years_span": self.years_span(),
            "mood_profile": self.mood_profile(),
            "top_artists": self.top_artists(n=10),
            "top_languages": self.top_languages(n=5),
            "top_decades": self.top_decades(n=3),
            "genre_distribution": self.genre_distribution(),
            "time_distribution": self.time_distribution(),
            "duplicate_count": self.duplicate_count(),
        }

    def total_songs(self) -> int:
        return len(self.songs)

    def total_duration(self) -> int:
        total = 0
        for s in self.songs:
            try:
                total += int(s.get("duration") or 0)
            except (TypeError, ValueError):
                pass
        return total

    def unique_count(self, field: str) -> int:
        values = set()
        for s in self.songs:
            v = s.get(field)
            if isinstance(v, str):
                values.add(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        values.add(item)
                    elif isinstance(item, dict) and "name" in item:
                        values.add(item["name"])
        return len(values)

    def explicit_ratio(self) -> float:
        if not self.songs:
            return 0.0
        explicit = sum(1 for s in self.songs if s.get("explicit"))
        return round(explicit / len(self.songs), 4)

    def avg_duration(self) -> float | None:
        durations = []
        for s in self.songs:
            try:
                d = int(s.get("duration") or 0)
                if d:
                    durations.append(d)
            except (TypeError, ValueError):
                pass
        return round(sum(durations) / len(durations), 1) if durations else None

    def years_span(self) -> dict[str, int | None]:
        years = []
        for s in self.songs:
            try:
                yr = int(s.get("year") or 0)
                if yr:
                    years.append(yr)
            except (TypeError, ValueError):
                pass
        if not years:
            return {"min": None, "max": None, "span": None}
        return {
            "min": min(years),
            "max": max(years),
            "span": max(years) - min(years),
        }

    def top_artists(self, n: int = 10) -> list[tuple[str, int]]:
        counter: Counter = Counter()
        for s in self.songs:
            artists = s.get("primary_artists", "")
            if isinstance(artists, str):
                for a in artists.split(","):
                    a = a.strip()
                    if a:
                        counter[a] += 1
            elif isinstance(artists, list):
                for a in artists:
                    if isinstance(a, str) and a.strip():
                        counter[a.strip()] += 1
        return counter.most_common(n)

    def top_languages(self, n: int = 5) -> list[tuple[str, int]]:
        counter: Counter = Counter()
        for s in self.songs:
            lang = s.get("language") or s.get("lang")
            if lang:
                counter[lang] += 1
        return counter.most_common(n)

    def top_decades(self, n: int = 3) -> list[tuple[int, int]]:
        counter: Counter = Counter()
        for s in self.songs:
            try:
                yr = int(s.get("year") or 0)
                if yr:
                    decade = (yr // 10) * 10
                    counter[decade] += 1
            except (TypeError, ValueError):
                pass
        return counter.most_common(n)

    # ── mood analysis ────────────────────────────────────────────────
    def mood_profile(self) -> dict[str, int]:
        from .Playlist import infer_mood
        counter: Counter = Counter()
        for s in self.songs:
            counter[infer_mood(s)] += 1
        return dict(counter.most_common())

    # ── distribution charts (data only) ──────────────────────────────
    def genre_distribution(self) -> dict[str, int]:
        """Map songs to genres based on mood + language + artist patterns."""
        counter: Counter = Counter()
        moods = self.mood_profile()
        languages = dict(self.top_languages(5))
        for mood, count in moods.items():
            # Convert mood → genre bucket
            if mood in ("party", "workout", "upbeat"):
                counter["upbeat"] += count
            elif mood == "romantic":
                counter["romantic"] += count
            elif mood in ("sad", "chill"):
                counter["chill"] += count
            elif mood == "devotional":
                counter["devotional"] += count
            else:
                counter["neutral"] += count
        # language buckets
        if "hindi" in languages:
            counter["hindi"] = languages["hindi"]
        if "english" in languages:
            counter["english"] = languages["english"]
        return dict(counter.most_common())

    def time_distribution(self) -> dict[str, int]:
        """Song distribution by year."""
        counter: Counter = Counter()
        for s in self.songs:
            try:
                yr = int(s.get("year") or 0)
                if yr:
                    counter[str(yr)] += 1
            except (TypeError, ValueError):
                pass
        return dict(sorted(counter.items()))

    # ── advanced analytics ───────────────────────────────────────────
    def duplicate_count(self) -> int:
        """Count songs that appear more than once (by normalized name + artist)."""
        from .Playlist import _norm
        seen: Counter = Counter()
        for s in self.songs:
            key = f"{_norm(s.get('name', ''))}|{_norm(s.get('primary_artists', ''))}"
            seen[key] += 1
        return sum(c - 1 for c in seen.values() if c > 1)

    def listening_velocity(self, years_span: dict | None = None) -> float:
        """Average songs per year in the collection."""
        span = years_span or self.years_span()
        if not span.get("span"):
            return float(len(self.songs))
        return round(len(self.songs) / max(span["span"], 1), 2)

    def diversity_score(self) -> float:
        """Shannon entropy across artists (0.0 = single artist, 1.0 = perfect diversity)."""
        counter: Counter = Counter()
        for s in self.songs:
            artists = s.get("primary_artists", "")
            if isinstance(artists, str):
                for a in artists.split(","):
                    a = a.strip()
                    if a:
                        counter[a] += 1
        total = sum(counter.values())
        if total <= 1:
            return 0.0
        entropy = 0.0
        for c in counter.values():
            p = c / total
            entropy -= p * math.log2(p)
        max_entropy = math_log2(len(counter)) if len(counter) > 1 else 1.0
        return round(entropy / max_entropy, 4)

    def artist_overlap(self, other_insights: "Insights") -> list[str]:
        """Artists shared between two insights."""
        my_artists = set()
        for s in self.songs:
            artists = s.get("primary_artists", "")
            if isinstance(artists, str):
                my_artists.update(a.strip() for a in artists.split(",") if a.strip())
        other_artists = set()
        for s in other_insights.songs:
            artists = s.get("primary_artists", "")
            if isinstance(artists, str):
                other_artists.update(a.strip() for a in artists.split(",") if a.strip())
        return sorted(my_artists & other_artists)

    # ── persistence ──────────────────────────────────────────────────
    def save(self) -> str:
        """Persist insights summary to SQLite. Returns the file path."""
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS insights (profile_id TEXT PRIMARY KEY, data TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO insights VALUES (?, ?, ?)",
            (
                self.profile_id,
                json.dumps(self.summary()),
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )
        conn.commit()
        conn.close()
        return _DB_PATH

    @staticmethod
    def load(profile_id: str = "default") -> dict | None:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        conn.execute("CREATE TABLE IF NOT EXISTS insights (profile_id TEXT PRIMARY KEY, data TEXT, updated_at TEXT)")
        row = conn.execute("SELECT data FROM insights WHERE profile_id = ?", (profile_id,)).fetchone()
        conn.close()
        if row is None:
            return None
        return json.loads(row[0])

    def __repr__(self) -> str:
        return f"Insights(songs={self.total_songs()}, id={self.profile_id!r})"


__all__ = ["Insights"]
