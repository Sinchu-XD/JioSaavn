"""DiscoveryGraph — music discovery via graph traversal.

Builds a local graph from JioSaavn suggestion edges and exposes
multiple traversal strategies:

* ``related_artists`` — find artists connected to a seed via suggestions.
* ``bridging_songs`` — songs that connect two different artist communities.
* ``community_explore`` — sample songs from a detected community.
* ``random_walk`` — breadth-first walk from seeds with depth control.

Usage::

    from JioSaavn.Analysis.DiscoveryGraph import DiscoveryGraph
    graph = await DiscoveryGraph.build(client, seed_ids=["s1", "s2"], depth=2)
    recs = graph.related_artists("artist_name", limit=10)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any


class _Graph:
    """Internal adjacency-list graph."""

    def __init__(self):
        self.edges: dict[str, set[str]] = defaultdict(set)
        self.nodes: set[str] = set()

    def add_edge(self, a: str, b: str) -> None:
        self.edges[a].add(b)
        self.edges[b].add(a)
        self.nodes.update([a, b])

    def neighbors(self, node: str) -> set[str]:
        return self.edges.get(node, set())

    def __len__(self) -> int:
        return len(self.nodes)


class DiscoveryGraph:
    """Song-to-song / artist-to-artist discovery graph.

    Built from JioSaavn's suggestion API as edges.  Once built, supports
    multiple traversal strategies without additional API calls.

    Parameters
    ----------
    graph:
        Pre-built ``_Graph`` instance.
    song_meta:
        Mapping of song_id → song dict (for enrichment, optional).
    client:
        API client used for lazy expansion.
    max_depth:
        Default walk depth.
    """

    def __init__(
        self,
        graph: _Graph,
        song_meta: dict[str, dict],
        client: Any,
        max_depth: int = 3,
    ):
        self._graph = graph
        self._song_meta = song_meta
        self._client = client
        self.max_depth = max_depth

    # ── build ────────────────────────────────────────────────────────
    @staticmethod
    async def build(
        client: Any,
        *,
        seed_ids: list[str],
        depth: int = 2,
        per_hop: int = 10,
        concurrency: int = 4,
    ) -> "DiscoveryGraph":
        """Fetch suggestions for each seed and build the graph up to *depth* hops."""
        graph = _Graph()
        song_meta: dict[str, dict] = {}

        seeds = list(dict.fromkeys(seed_ids))  # dedup, preserve order
        for sid in seeds:
            graph.nodes.add(sid)

        frontier = list(seeds)
        seen = set(frontier)
        sem = asyncio.Semaphore(concurrency)

        for _ in range(depth):
            next_frontier: list[str] = []

            async def walk(node: str) -> None:
                async with sem:
                    try:
                        sug = await client.get_suggestions(node, limit=per_hop)
                    except Exception:
                        return
                for s in sug or []:
                    cid = s.get("id") or s.get("songid")
                    if not cid or cid in seen:
                        continue
                    seen.add(cid)
                    next_frontier.append(cid)
                    graph.add_edge(node, cid)
                    song_meta.setdefault(cid, s)

            await asyncio.gather(*[walk(node) for node in frontier])
            frontier = next_frontier
            if not frontier:
                break

        return DiscoveryGraph(graph, song_meta, client, max_depth=depth)

    # ── graph helpers ────────────────────────────────────────────────
    def related_artists(self, artist_name: str, limit: int = 10) -> list[dict]:
        """Find songs by artists reachable from songs whose primary_artists
        contain *artist_name*."""
        # find seed songs
        seed_songs = [
            s for s in self._song_meta.values()
            if artist_name.lower() in str(s.get("primary_artists", "")).lower()
        ]
        seed_ids = [s.get("id") or s.get("songid") for s in seed_songs]

        # BFS 1 hop from seeds
        visited = set(seed_ids)
        candidates: list[dict] = []
        for sid in seed_ids:
            for nid in self._graph.neighbors(sid):
                if nid not in visited:
                    visited.add(nid)
                    if meta := self._song_meta.get(nid):
                        candidates.append(meta)

        # dedupe & rank by degree (most connected = most similar)
        seen_ids: set[str] = set()
        ranked: list[tuple[dict, int]] = []
        for s in candidates:
            cid = s.get("id") or s.get("songid")
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            degree = len(self._graph.edges.get(cid, set()))
            ranked.append((s, degree))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:limit]]

    def bridging_songs(
        self, artist_a: str, artist_b: str, limit: int = 10
    ) -> list[dict]:
        """Find songs that connect songs by *artist_a* and songs by *artist_b*."""
        a_songs = {
            s.get("id") or s.get("songid")
            for s in self._song_meta.values()
            if artist_a.lower() in str(s.get("primary_artists", "")).lower()
        }
        b_songs = {
            s.get("id") or s.get("songid")
            for s in self._song_meta.values()
            if artist_b.lower() in str(s.get("primary_artists", "")).lower()
        }

        # Find songs connected to both sets
        bridging: dict[str, tuple[dict, int]] = {}
        for a in a_songs:
            for neighbor in self._graph.neighbors(a):
                if neighbor in b_songs:
                    continue
                if meta := self._song_meta.get(neighbor):
                    a_deg = len(self._graph.edges.get(a, set()))
                    b_deg = len(self._graph.edges.get(neighbor, set()))
                    score = a_deg + b_deg
                    if neighbor not in bridging or score > bridging[neighbor][1]:
                        bridging[neighbor] = (meta, score)

        ranked = sorted(bridging.values(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in ranked[:limit]]

    def community_explore(
        self, seed_id: str, limit: int = 15
    ) -> list[dict]:
        """Sample songs from the community around *seed_id* using BFS."""
        visited = {seed_id}
        queue: deque[str] = deque([seed_id])
        community: list[dict] = []
        while queue and len(community) < limit:
            node = queue.popleft()
            if meta := self._song_meta.get(node):
                community.append(meta)
            for nid in self._graph.neighbors(node):
                if nid not in visited:
                    visited.add(nid)
                    queue.append(nid)
        return community[:limit]

    def random_walk(
        self, seed_ids: list[str], limit: int = 20, steps: int = 4
    ) -> list[dict]:
        """Simulate a random walk from each seed, collect results."""
        import random
        results: list[tuple[dict, float]] = []
        seen_ids: set[str] = set()

        for sid in seed_ids:
            current = sid
            for _ in range(steps):
                neighbors = list(self._graph.neighbors(current))
                if not neighbors:
                    break
                current = random.choice(neighbors)
                if current in seen_ids:
                    continue
                seen_ids.add(current)
                if meta := self._song_meta.get(current):
                    degree = len(self._graph.edges.get(current, set()))
                    results.append((meta, degree))

        results.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in results[:limit]]

    # ── metadata ────────────────────────────────────────────────────
    def graph_stats(self) -> dict[str, Any]:
        """Return graph size and density info."""
        node_count = len(self._graph.nodes)
        edge_count = sum(len(v) for v in self._graph.edges.values()) // 2
        max_edges = node_count * (node_count - 1) // 2
        density = edge_count / max_edges if max_edges else 0.0
        degrees = [(nid, len(self._graph.edges.get(nid, set())))
                   for nid in self._graph.nodes]
        degrees.sort(key=lambda x: x[1], reverse=True)
        top_nodes = [nid for nid, _ in degrees[:10]]
        return {
            "nodes": node_count,
            "edges": edge_count,
            "density": round(density, 6),
            "top_connected": top_nodes,
            "songs_in_meta": len(self._song_meta),
        }

    def __repr__(self) -> str:
        return (
            f"DiscoveryGraph(nodes={len(self._graph.nodes)}, "
            f"edges={sum(len(v) for v in self._graph.edges.values()) // 2})"
        )


__all__ = ["DiscoveryGraph"]
