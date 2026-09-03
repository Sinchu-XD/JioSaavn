"""TasteProfile — a user's musical fingerprint.

Computes weighted taste features from a song list (languages, artists, moods,
decades, duration preferences) and persists them to SQLite.

Usage::

    from JioSaavn.Analysis.TasteProfile import TasteProfile, build_profile

    profile = await build_profile(songs)
    print(profile.summary())
    sim = profile.similarity(other_profile)
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter
from typing import Any


# ── SQLite helpers ────────────────────────────────────────────────────
_DB_PATH = "saavn_downloads.db"

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS taste_profiles (
    profile_id   TEXT PRIMARY KEY,
    features_json TEXT NOT NULL,
    song_ids_json TEXT NOT NULL,
    updated_at   TEXT NOT NULL
)
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute(_TABLE_DDL)
    conn.commit()
    return conn


def _row_to_profile(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "features": json.loads(row["features_json"]),
        "song_ids": json.loads(row["song_ids_json"]),
        "updated_at": row["updated_at"],
    }


# ── Feature extraction ────────────────────────────────────────────────
def _lang(s: dict) -> str | None:
    return s.get("language") or s.get("lang")


def _year(s: dict) -> int | None:
    try:
        return int(s.get("year") or 0) or None
    except (TypeError, ValueError):
        return None


def _duration(s: dict) -> int | None:
    raw = s.get("duration") or s.get("more_info", {}).get("duration")
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


def _extract_features(songs: list[dict]) -> dict[str, Any]:
    """Return normalized feature vectors from a list of song dicts."""
    languages: Counter = Counter()
    artists: Counter = Counter()
    moods: Counter = Counter()
    decades: Counter = Counter()
    durations: list[int] = []
    explicit = 0
    total = len(songs)

    from .Playlist import _artists_of, infer_mood  # lazy to avoid cycles

    for s in songs:
        if lang := _lang(s):
            languages[lang] += 1
        for a in _artists_of(s):
            if a:
                artists[a] += 1
        moods[infer_mood(s)] += 1
        if yr := _year(s):
            decades[(yr // 10) * 10] += 1
        if dur := _duration(s):
            durations.append(dur)
        if s.get("explicit"):
            explicit += 1

    def _normalize(counter: Counter) -> dict[str, float]:
        if not counter:
            return {}
        return {k: round(v / total, 4) for k, v in counter.most_common(50)}

    return {
        "languages": _normalize(languages),
        "artists": _normalize(artists),
        "moods": _normalize(moods),
        "decades": _normalize(decades),
        "avg_duration": round(sum(durations) / len(durations), 1) if durations else None,
        "explicit_ratio": round(explicit / total, 4) if total else 0.0,
        "total_songs": total,
    }


# ── Cosine similarity ─────────────────────────────────────────────────
def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    mag_a = sum(v ** 2 for v in a.values()) ** 0.5
    mag_b = sum(v ** 2 for v in b.values()) ** 0.5
    denom = mag_a * mag_b
    return dot / denom if denom else 0.0


# ── TasteProfile class ────────────────────────────────────────────────
class TasteProfile:
    """Immutable-ish musical taste fingerprint.

    Create with ``TasteProfile(profile_id="default")`` and call
    ``add_songs(songs)`` to accumulate features.  Persist with ``save()``,
    reload with ``TasteProfile.load(profile_id)``.
    """

    def __init__(self, profile_id: str = "default", features: dict | None = None,
                 song_ids: list[str] | None = None):
        self.profile_id = profile_id
        self.features: dict[str, Any] = features or {
            "languages": {}, "artists": {}, "moods": {},
            "decades": {}, "avg_duration": None,
            "explicit_ratio": 0.0, "total_songs": 0,
        }
        self._song_ids: set[str] = set(song_ids or [])

    # ── mutation ──────────────────────────────────────────────────────
    def _song_id(self, s: dict) -> str:
        return str(s.get("id") or s.get("songid") or "")

    def _merge_features(self, new_features: dict) -> None:
        """Merge a fresh feature dict into self.features using weighted average."""
        old_total = self.features.get("total_songs", 0)
        new_total = new_features.get("total_songs", 0)
        if new_total == 0:
            return

        combined_total = old_total + new_total

        def _merge(counter_key: str) -> dict[str, float]:
            merged: Counter = Counter()
            for k, v in self.features.get(counter_key, {}).items():
                merged[k] = v * old_total
            for k, v in new_features.get(counter_key, {}).items():
                merged[k] += v * new_total
            return {k: round(v / combined_total, 4) for k, v in merged.most_common(50)}

        self.features["languages"] = _merge("languages")
        self.features["artists"] = _merge("artists")
        self.features["moods"] = _merge("moods")
        self.features["decades"] = _merge("decades")

        old_dur = self.features.get("avg_duration") or 0
        new_dur = new_features.get("avg_duration") or 0
        self.features["avg_duration"] = round(
            (old_dur * old_total + new_dur * new_total) / combined_total, 1
        ) if combined_total else None

        old_ex = self.features.get("explicit_ratio", 0.0) * old_total
        new_ex = new_features.get("explicit_ratio", 0.0) * new_total
        self.features["explicit_ratio"] = round((old_ex + new_ex) / combined_total, 4)
        self.features["total_songs"] = combined_total

    def add_songs(self, songs: list[dict]) -> int:
        """Add songs to the profile. Returns count of *new* songs added."""
        new_ids: set[str] = set()
        new_songs: list[dict] = []
        for s in songs:
            sid = self._song_id(s)
            if sid and sid not in self._song_ids:
                new_ids.add(sid)
                new_songs.append(s)

        if not new_songs:
            return 0

        feats = _extract_features(new_songs)
        self._merge_features(feats)
        self._song_ids.update(new_ids)
        return len(new_songs)

    # ── persistence ───────────────────────────────────────────────────
    def save(self) -> None:
        """Persist profile to SQLite (thread-safe, SQLite is serialized)."""
        self._save_sync()

    def _save_sync(self) -> None:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO taste_profiles (profile_id, features_json, song_ids_json, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (
                self.profile_id,
                json.dumps(self.features),
                json.dumps(list(self._song_ids)),
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            ),
        )
        conn.commit()
        conn.close()

    @classmethod
    def load(cls, profile_id: str = "default") -> "TasteProfile | None":
        """Load a persisted profile from SQLite, or None if not found."""
        conn = _get_conn()
        row = conn.execute(
            "SELECT features_json, song_ids_json FROM taste_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return cls(
            profile_id=profile_id,
            features=json.loads(row["features_json"]),
            song_ids=json.loads(row["song_ids_json"]),
        )

    # ── queries ───────────────────────────────────────────────────────
    def similarity(self, other: "TasteProfile") -> float:
        """Cosine similarity between two taste profiles (0.0–1.0)."""
        return _cosine_similarity(self.features["languages"], other.features["languages"]) * 0.25 \
            + _cosine_similarity(self.features["artists"], other.features["artists"]) * 0.30 \
            + _cosine_similarity(self.features["moods"], other.features["moods"]) * 0.25 \
            + _cosine_similarity(self.features["decades"], other.features["decades"]) * 0.20

    def top_artists(self, n: int = 10) -> list[tuple[str, float]]:
        return list(self.features.get("artists", {}).items())[:n]

    def top_languages(self, n: int = 5) -> list[tuple[str, float]]:
        return list(self.features.get("languages", {}).items())[:n]

    def top_moods(self, n: int = 5) -> list[tuple[str, float]]:
        return list(self.features.get("moods", {}).items())[:n]

    def top_decades(self, n: int = 3) -> list[tuple[int, float]]:
        return [(int(k), v) for k, v in list(self.features.get("decades", {}).items())[:n]]

    def summary(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "total_songs": self.features.get("total_songs", 0),
            "top_languages": self.top_languages(),
            "top_artists": self.top_artists(),
            "top_moods": self.top_moods(),
            "top_decades": self.top_decades(),
            "avg_duration_sec": self.features.get("avg_duration"),
            "explicit_ratio": self.features.get("explicit_ratio"),
        }

    def __repr__(self) -> str:
        return f"TasteProfile(id={self.profile_id!r}, songs={self.features['total_songs']})"


# ── Convenience helpers ───────────────────────────────────────────────
def build_profile(songs: list[dict], profile_id: str = "default") -> TasteProfile:
    """Build a TasteProfile from a list of song dicts."""
    profile = TasteProfile(profile_id=profile_id)
    added = profile.add_songs(songs)
    return profile


def load_or_build(songs: list[dict], profile_id: str = "default") -> TasteProfile:
    """Load existing profile and merge new songs, or build from scratch."""
    profile = TasteProfile.load(profile_id)
    if profile is None:
        profile = build_profile(songs, profile_id=profile_id)
        profile.save()
    else:
        added = profile.add_songs(songs)
        if added:
            profile.save()
    return profile


__all__ = ["TasteProfile", "build_profile", "load_or_build"]
