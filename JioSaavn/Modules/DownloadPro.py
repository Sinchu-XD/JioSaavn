"""Download Manager Pro — persistent queue, resume, embedded lyrics, video."""
from __future__ import annotations
import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional
import aiohttp


class DownloadManager:
    """Persistent download queue backed by SQLite. Resumable and inspectable."""

    def __init__(self, db_path: str = "saavn_downloads.db", concurrency: int = 3):
        self.db_path = db_path
        self.concurrency = concurrency
        self._sem = asyncio.Semaphore(concurrency)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, song_json TEXT NOT NULL,
                out_path TEXT NOT NULL, bitrate INTEGER DEFAULT 320,
                status TEXT DEFAULT 'pending', bytes_done INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0, error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")

    def enqueue(self, song: dict, out_path: str, bitrate: int = 320) -> str:
        sid = song.get("id") or song.get("songid") or out_path
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO jobs (id, song_json, out_path, bitrate, status) VALUES (?, ?, ?, ?, 'pending')",
                (sid, json.dumps(song), out_path, bitrate),
            )
        return sid

    def list_jobs(self, status: Optional[str] = None) -> list[dict]:
        q = "SELECT id, out_path, status, bytes_done, total_bytes, error FROM jobs"
        args = ()
        if status:
            q += " WHERE status = ?"; args = (status,)
        with self._conn() as c:
            return [dict(zip(["id", "out_path", "status", "bytes_done", "total_bytes", "error"], r))
                    for r in c.execute(q, args).fetchall()]

    def pause(self, job_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE jobs SET status='paused' WHERE id=?", (job_id,))

    def resume(self, job_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE jobs SET status='pending' WHERE id=?", (job_id,))

    async def _download_one(self, job: tuple) -> None:
        jid, song_json, out_path, bitrate, bytes_done = job
        song = json.loads(song_json)
        url = _pick_stream(song, bitrate)
        if not url:
            with self._conn() as c:
                c.execute("UPDATE jobs SET status='failed', error='no stream url' WHERE id=?", (jid,))
            return
        out = Path(out_path); out.parent.mkdir(parents=True, exist_ok=True)
        headers = {"Range": f"bytes={bytes_done}-"} if bytes_done else {}
        mode = "ab" if bytes_done else "wb"
        try:
            async with self._sem, aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as r:
                    r.raise_for_status()
                    total = bytes_done + int(r.headers.get("Content-Length", 0))
                    with open(out, mode) as f:
                        with self._conn() as c:
                            c.execute("UPDATE jobs SET status='downloading', total_bytes=? WHERE id=?", (total, jid))
                        async for chunk in r.content.iter_chunked(64 * 1024):
                            f.write(chunk); bytes_done += len(chunk)
                            with self._conn() as c:
                                c.execute("UPDATE jobs SET bytes_done=? WHERE id=?", (bytes_done, jid))
            with self._conn() as c:
                c.execute("UPDATE jobs SET status='done' WHERE id=?", (jid,))
        except Exception as e:
            with self._conn() as c:
                c.execute("UPDATE jobs SET status='failed', error=? WHERE id=?", (str(e), jid))

    async def run(self) -> None:
        """Process all pending jobs. Safe to call repeatedly."""
        with self._conn() as c:
            jobs = c.execute(
                "SELECT id, song_json, out_path, bitrate, bytes_done FROM jobs WHERE status IN ('pending','downloading')"
            ).fetchall()
        await asyncio.gather(*(self._download_one(j) for j in jobs))


def _pick_stream(song: dict, bitrate: int) -> Optional[str]:
    urls = song.get("download_url") or song.get("more_info", {}).get("download_url")
    if isinstance(urls, list):
        # 1) exact match
        for u in urls:
            if int(u.get("quality", "0").rstrip("kbps") or 0) == bitrate:
                return u.get("link") or u.get("url")
        # 2) highest available bitrate
        best = None
        best_q = -1
        for u in urls:
            q = int(u.get("quality", "0").rstrip("kbps") or 0)
            if q > best_q:
                best_q = q
                best = u.get("link") or u.get("url")
        return best
    return song.get("media_url")


async def download_with_lyrics(client: Any, song_id: str, out_path: str, bitrate: int = 320) -> str:
    """Download a song and embed synced lyrics into the MP3 (USLT frame)."""
    song = await client.get_song(song_id)
    dm = DownloadManager()
    dm.enqueue(song, out_path, bitrate)
    await dm.run()
    try:
        lyr = await client.get_lyrics(song_id)
        text = (lyr or {}).get("lyrics", "") if isinstance(lyr, dict) else str(lyr or "")
        if text:
            from mutagen.id3 import ID3, USLT
            try:
                tags = ID3(out_path)
            except Exception:
                tags = ID3(); tags.save(out_path); tags = ID3(out_path)
            tags.add(USLT(encoding=3, lang="eng", desc="", text=text))
            tags.save(out_path)
    except Exception:
        pass
    return out_path
