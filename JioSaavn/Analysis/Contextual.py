"""Contextual recommendations — adjusts recommendations based on time, day, season.

Wraps ``RecommendationEngine`` and adds context-aware score adjustments:

* **Time of day** — morning (upbeat), work hours (instrumental/calm),
  evening (chill), night (slow/romantic).
* **Day of week** — weekdays (calm, work-appropriate), weekends (party).
* **Season** — summer (upbeat), monsoon/rainy (romantic), winter (cozy).

Usage::

    from JioSaavn.Analysis.Contextual import ContextualRecommender
    from JioSaavn.Analysis.RecommendationEngine import RecommendationEngine
    from JioSaavn.Analysis.TasteProfile import build_profile

    engine = RecommendationEngine(client=client, taste_profile=profile)
    ctx = ContextualRecommender(engine)
    recs = await ctx.get_recommendations(seed_ids, limit=20)
"""
from __future__ import annotations

import datetime
from typing import Any

from .RecommendationEngine import RecommendationEngine


_TIME_WINDOWS = {
    # (start_hour, end_hour): (mood_boost, genre_nudge)
    (5, 8):    ({"morning": 0.20},   {"energetic": 0.15, "upbeat": 0.15, "romantic": 0.05}),  # early morning
    (8, 11):   ({"work": 0.15},      {"instrumental": 0.10, "chill": 0.10}),                 # work
    (11, 14):  ({"party": 0.10},     {"upbeat": 0.10, "dance": 0.10}),                       # midday
    (14, 17):  ({"chill": 0.10},     {"acoustic": 0.10, "relax": 0.10}),                    # afternoon
    (17, 20):  ({"party": 0.15},     {"upbeat": 0.10, "dance": 0.10, "energetic": 0.10}), # evening
    (20, 23):  ({"chill": 0.15},     {"romantic": 0.10, "acoustic": 0.05}),                 # night
    (23, 24):  ({"romantic": 0.20},  {"slow": 0.15, "chill": 0.10}),                       # late night
    (0, 5):    ({"romantic": 0.20},  {"slow": 0.15, "chill": 0.10}),                       # deep night
}

_WEEKEND_MOODS = {"party": 0.15, "upbeat": 0.10, "energetic": 0.10}
_WEEKDAY_MOODS = {"chill": 0.10, "work": 0.10, "instrumental": 0.05}

_SEASON_MAP = {
    # month → (mood_boost, vibe)
    0:  ("cozy",    {"romantic": 0.10, "slow": 0.10, "devotional": 0.05}),
    1:  ("cozy",    {"romantic": 0.10, "slow": 0.10, "devotional": 0.05}),
    2:  ("spring",  {"fresh": 0.10, "upbeat": 0.05, "chill": 0.05}),
    3:  ("summer",  {"energetic": 0.10, "upbeat": 0.10, "dance": 0.05}),
    4:  ("summer",  {"energetic": 0.10, "upbeat": 0.10, "dance": 0.05}),
    5:  ("monsoon", {"romantic": 0.15, "chill": 0.10, "slow": 0.05}),
    6:  ("monsoon", {"romantic": 0.15, "chill": 0.10, "slow": 0.05}),
    7:  ("summer",  {"energetic": 0.10, "upbeat": 0.10, "dance": 0.05}),
    8:  ("summer",  {"energetic": 0.10, "upbeat": 0.10, "dance": 0.05}),
    9:  ("autumn",  {"chill": 0.10, "acoustic": 0.10, "slow": 0.05}),
    10: ("autumn",  {"chill": 0.10, "acoustic": 0.10, "slow": 0.05}),
    11: ("winter",  {"cozy": 0.10, "romantic": 0.10, "devotional": 0.05}),
}


class ContextualRecommender:
    """Wraps a ``RecommendationEngine`` and adjusts scores for context.

    Parameters
    ----------
    engine:
        The underlying recommendation engine.
    user_timezone:
        UTC offset in hours (e.g. ``5.5`` for IST).  Default ``0`` (UTC).
    enable_time:
        Enable time-of-day adjustments.
    enable_day:
        Enable weekday/weekend adjustments.
    enable_season:
        Enable seasonal adjustments.
    """

    def __init__(
        self,
        engine: RecommendationEngine,
        *,
        user_timezone: float = 0.0,
        enable_time: bool = True,
        enable_day: bool = True,
        enable_season: bool = True,
    ):
        self.engine = engine
        self.user_timezone = user_timezone
        self.enable_time = enable_time
        self.enable_day = enable_day
        self.enable_season = enable_season

    # ── public API ───────────────────────────────────────────────────
    async def get_recommendations(
        self,
        seed_ids: list[str],
        *,
        limit: int = 20,
        context: dict | None = None,
    ) -> list[dict]:
        """Return contextually boosted recommendations.

        Parameters
        ----------
        seed_ids:
            Seed song IDs to base recommendations on.
        limit:
            Max number of results.
        context:
            Optional override dict with keys ``hour``, ``day``, ``month``.
        """
        base_recs = await self.engine.get_recommendations(seed_ids, limit=limit * 2)
        if not base_recs:
            return []

        ctx = context or self._current_context()
        boosted = self._apply_context(base_recs, ctx)
        return boosted[:limit]

    def get_current_context(self) -> dict[str, Any]:
        """Return the computed context dict (for logging / display)."""
        return self._current_context()

    # ── context computation ──────────────────────────────────────────
    def _current_context(self) -> dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc)
        local = now + datetime.timedelta(hours=self.user_timezone)
        hour = local.hour
        dow = local.weekday()  # 0=Mon … 6=Sun
        month = local.month

        # time window
        time_window = None
        time_mood_boosts: dict[str, float] = {}
        if self.enable_time:
            for (lo, hi), (moods, _) in _TIME_WINDOWS.items():
                if lo <= hour < hi or (hi == 24 and lo <= hour):
                    time_window = f"{lo:02d}:00-{hi:02d}:00"
                    time_mood_boosts = {m: b for m, b in moods.items()}
                    break

        # day
        day_type = "weekend" if dow >= 5 else "weekday"
        day_mood_boosts = _WEEKEND_MOODS if dow >= 5 else _WEEKDAY_MOODS
        if not self.enable_day:
            day_mood_boosts = {}

        # season
        season_name, season_boosts = _SEASON_MAP.get(month, ("unknown", {}))
        if not self.enable_season:
            season_boosts = {}

        return {
            "hour": hour,
            "day_of_week": dow,
            "day_type": day_type,
            "month": month,
            "season": season_name,
            "time_window": time_window,
            "mood_boosts": {**time_mood_boosts, **day_mood_boosts, **season_boosts},
        }

    # ── scoring ─────────────────────────────────────────────────────
    def _apply_context(
        self, candidates: list[dict], context: dict
    ) -> list[dict]:
        """Adjust each candidate's score based on context mood boosts."""
        mood_boosts: dict[str, float] = context.get("mood_boosts", {})

        # Delegate mood inference to the existing infer_mood
        from .Playlist import infer_mood

        scored: list[tuple[dict, float]] = []
        for s in candidates:
            # Base score: position-based (earlier = better)
            base = max(0.0, 1.0 - (candidates.index(s) / max(len(candidates), 1))) * 0.5

            # Context boost
            song_mood = infer_mood(s)
            boost = mood_boosts.get(song_mood, 0.0)

            score = base + boost
            scored.append((s, score))

        return [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


__all__ = ["ContextualRecommender"]
