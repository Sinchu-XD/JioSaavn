"""RecommendationEngine — multi-strategy ranked recommendations.

Combines three signals:

1. **Taste alignment** — songs matching the user's TasteProfile (artists,
   languages, moods) score higher.
2. **History co-occurrence** — `get_suggestions(seed)` returns songs that
   appear near the seed in JioSaavn's graph.
3. **Freshness** — newer songs get a small boost so the feed doesn't go stale.

Usage::

    from JioSaavn.Analysis.RecommendationEngine import RecommendationEngine
    from JioSaavn.Analysis.TasteProfile import TasteProfile, build_profile

    engine = RecommendationEngine(client=client, taste_profile=profile)
    recs = await engine.get_recommendations(seed_ids, limit=20)
"""
from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

from ..Utils.Cache import AsyncTTLCache
from .TasteProfile import TasteProfile, _extract_features, _cosine_similarity


class RecommendationEngine:
    """Multi-signal recommendation engine.

    Parameters
    ----------
    client:
        A ``JioSaavnClient`` instance used for API calls.
    taste_profile:
        Pre-built ``TasteProfile``.  If *None* recommendations fall back to
        history-only scoring.
    cache_ttl:
        How long (seconds) to cache recommendation results per seed set.
    """

    def __init__(
        self,
        client: Any,
        taste_profile: TasteProfile | None = None,
        cache_ttl: float = 120.0,
    ):
        self.client = client
        self.taste_profile = taste_profile
        self._cache = AsyncTTLCache(maxsize=256, ttl=cache_ttl)

    # ── public API ────────────────────────────────────────────────────
    async def get_recommendations(
        self,
        seed_ids: list[str],
        *,
        limit: int = 20,
        fresh_boost: float = 0.05,
    ) -> list[dict]:
        """Return a ranked list of recommended song dicts.

        Seeds are de-duped and limited to the last 8 to keep latency down.
        """
        seed_key = tuple(dict.fromkeys(seed_ids))  # dedup, preserve order
        cache_key = ("recs", seed_key, limit)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached[:limit]

        candidates = await self._gather_candidates(seed_ids[-8:])
        ranked = self._rank(candidates, fresh_boost=fresh_boost)
        result = ranked[:limit]

        await self._cache.set(cache_key, result)
        return result

    async def recommend_for_history(
        self,
        history: list[str],
        *,
        limit: int = 20,
    ) -> list[dict]:
        """Convenience wrapper — build a taste profile from history then recommend."""
        history = history[-50:]  # cap to avoid O(n^2) feature extraction
        if self.taste_profile is None:
            self.taste_profile = TasteProfile()

        # cheap batch: build a temp profile to score candidates
        from . import recommend_from_history  # avoid circular
        sug = await recommend_from_history(self.client, history, limit=limit * 2)
        if not sug:
            return []

        # score by taste alignment
        scored = self._score_by_taste(sug)
        return [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)][:limit]

    async def clear_cache(self) -> None:
        await self._cache.clear()

    def cache_stats(self) -> dict:
        return self._cache.stats()

    # ── candidate gathering ───────────────────────────────────────────
    async def _gather_candidates(self, seed_ids: list[str]) -> list[dict]:
        """Fetch suggestions for each seed and collect unique candidates."""
        seen: set[str] = set(seeds_set := set(seed_ids))
        candidates: list[dict] = []

        sem = asyncio.Semaphore(4)

        async def fetch(seed: str) -> None:
            async with sem:
                try:
                    sug = await self.client.get_suggestions(seed, limit=15)
                except Exception:
                    return
            for s in sug or []:
                cid = str(s.get("id") or s.get("songid") or "")
                if cid and cid not in seen:
                    seen.add(cid)
                    candidates.append(s)

        await asyncio.gather(*[fetch(sid) for sid in seed_ids], return_exceptions=True)
        return candidates

    # ── scoring ───────────────────────────────────────────────────────
    def _rank(self, candidates: list[dict], fresh_boost: float = 0.05) -> list[dict]:
        """Score and sort candidates.  Songs with no year get a tiny penalty."""
        scored: list[tuple[dict, float]] = []
        for s in candidates:
            score = 0.5  # base
            if self.taste_profile:
                score = max(score, self._taste_score(s))

            # freshness: newer songs get a small bump
            try:
                yr = int(s.get("year") or 0)
                if yr:
                    import datetime
                    age = max(0, datetime.datetime.now().year - yr)
                    score += fresh_boost * max(0, 1 - age / 20)
            except (TypeError, ValueError):
                score -= 0.05  # unknown year → slight penalty

            scored.append((s, score))

        return [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)]

    def _score_by_taste(self, songs: list[dict]) -> list[tuple[dict, float]]:
        return [(s, self._taste_score(s)) for s in songs]

    def _taste_score(self, song: dict) -> float:
        """Compute how well *song* matches the taste profile (0.0–1.0)."""
        if self.taste_profile is None:
            return 0.5

        feats = self.taste_profile.features
        song_features = _extract_features([song])
        score = 0.0

        if feats.get("languages") and song_features.get("languages"):
            score += _cosine_similarity(feats["languages"], song_features["languages"]) * 0.25

        if feats.get("moods") and song_features.get("moods"):
            score += _cosine_similarity(feats["moods"], song_features["moods"]) * 0.25

        if feats.get("artists") and song_features.get("artists"):
            score += _cosine_similarity(feats["artists"], song_features["artists"]) * 0.30

        if feats.get("decades") and song_features.get("decades"):
            score += _cosine_similarity(feats["decades"], song_features["decades"]) * 0.20

        # boost if song language matches dominant language
        top_lang = next(iter(feats.get("languages", {})), None)
        if top_lang and song.get("language") == top_lang:
            score += 0.10

        # boost if any artist matches
        from .Playlist import _artists_of
        song_artists = {a.lower() for a in _artists_of(song) if a}
        profile_artists = {a.lower() for a in feats.get("artists", {})}
        if song_artists & profile_artists:
            score += 0.20

        return min(1.0, score)


__all__ = ["RecommendationEngine"]
