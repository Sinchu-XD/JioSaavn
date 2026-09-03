"""Playlist analysis — stats, duplicate detection, mood inference."""
from __future__ import annotations
from collections import Counter
from difflib import SequenceMatcher
from typing import Iterable


def _norm(s: str) -> str:
    return "".join(c.lower() for c in (s or "") if c.isalnum())


def analyze_playlist(songs: list[dict]) -> dict:
    """Return statistics: duration, languages, top artists, decade breakdown."""
    if not songs:
        return {"count": 0}

    total_duration = 0
    languages: Counter = Counter()
    artists: Counter = Counter()
    albums: Counter = Counter()
    years: Counter = Counter()
    explicit = 0

    for s in songs:
        try:
            total_duration += int(s.get("duration") or 0)
        except (TypeError, ValueError):
            pass
        if lang := s.get("language"):
            languages[lang] += 1
        if s.get("explicit"):
            explicit += 1
        for a in _artists_of(s):
            artists[a] += 1
        if alb := (s.get("album") or {}).get("name") if isinstance(s.get("album"), dict) else s.get("album"):
            albums[str(alb)] += 1
        yr = s.get("year")
        if yr:
            try:
                years[(int(yr) // 10) * 10] += 1
            except (TypeError, ValueError):
                pass

    return {
        "count": len(songs),
        "total_duration_seconds": total_duration,
        "total_duration_human": _fmt_duration(total_duration),
        "explicit_count": explicit,
        "top_languages": languages.most_common(5),
        "top_artists": artists.most_common(10),
        "top_albums": albums.most_common(10),
        "decade_breakdown": dict(sorted(years.items())),
        "dominant_language": languages.most_common(1)[0][0] if languages else None,
    }


def find_duplicates(songs: list[dict], threshold: float = 0.9) -> list[tuple[dict, dict, float]]:
    """Fuzzy-match duplicates. Returns (a, b, similarity) tuples."""
    pairs: list[tuple[dict, dict, float]] = []
    keys = [(s, f"{_norm(s.get('name', ''))}|{_norm(','.join(_artists_of(s)))}") for s in songs]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            r = SequenceMatcher(None, keys[i][1], keys[j][1]).ratio()
            if r >= threshold:
                pairs.append((keys[i][0], keys[j][0], round(r, 3)))
    return pairs


MOOD_KEYWORDS = {
    "romantic": [
        "love", "romance", "heart", "kiss", "pyar", "ishq", "mohabbat",
        "jaan", "dil", "teda", "sajni", "intzaar", "mulaqat", "sajna",
    ],
    "party": [
        "party", "dance", "club", "beat", "dj", "nachle", "masti",
        "hangover", "remix", "pump", "groove",
    ],
    "sad": [
        "sad", "tears", "cry", "alone", "broken", "judai", "bewafa",
        "dard", "dukh", "tanhaai", "bekarar", "aansu",
    ],
    "workout": [
        "power", "energy", "fire", "warrior", "beast", "pump", "strong",
        "fight", "rise", "unstoppable",
    ],
    "chill": [
        "chill", "relax", "calm", "peace", "acoustic", "slow", "lofi",
        "sufi", "qawwali",
    ],
    "devotional": [
        "bhajan", "aarti", "kirtan", "prayer", "god", "allah", "ram",
        "krishna", "shiva", "bhagwan", "ishwar", "divine", "mandir",
        "gurbani",
    ],
    "upbeat": [
        "zara", "jab tak", "jab", "phir", "dil", "baar", "bada", "badi",
        "high", "josh", "jhatka", "mast", "rang", "rang de", "jhoom",
    ],
}


def infer_mood(song: dict) -> str:
    """Infer mood label from song title + primary_artists + duration hint.

    Scoring is now multi-source:
    * Title / subtitle keyword match (highest weight)
    * Primary artists hint (e.g., "Yo Yo Honey Singh" → party)
    * Duration heuristic (≤180s → upbeat/party, ≥300s → romantic/chill)
    """
    scores: dict[str, float] = {mood: 0.0 for mood in MOOD_KEYWORDS}
    title = " ".join(str(song.get(k, "")) for k in ("name", "title", "subtitle", "description"))
    artists = str(song.get("primary_artists", ""))
    haystack = f"{title} {artists}".lower()

    for mood, kws in MOOD_KEYWORDS.items():
        for kw in kws:
            if kw in haystack:
                scores[mood] += 1.0  # keyword hit

    # Duration heuristic (minor)
    try:
        dur = int(song.get("duration") or 0)
        if dur and dur <= 180:
            scores["upbeat"] += 0.5
            scores["party"] += 0.3
        elif dur >= 300:
            scores["romantic"] += 0.3
            scores["chill"] += 0.3
    except (TypeError, ValueError):
        pass

    best_mood, best_score = max(scores.items(), key=lambda x: x[1])
    return best_mood if best_score > 0 else "neutral"


def _artists_of(s: dict) -> list[str]:
    if isinstance(s.get("primary_artists"), str):
        return [a.strip() for a in s["primary_artists"].split(",") if a.strip()]
    if isinstance(s.get("artists"), list):
        return [a.get("name", "") if isinstance(a, dict) else str(a) for a in s["artists"]]
    if isinstance(s.get("artist_map"), dict):
        return [a.get("name", "") for a in s["artist_map"].get("primary_artists", []) if isinstance(a, dict)]
    return []


def _fmt_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
