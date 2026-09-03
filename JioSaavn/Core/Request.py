import asyncio
import json

import aiohttp

from .Parser import extract_json
from .Errors import APIError, NetworkError

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)
MAX_RETRIES = 3


class Request:
    def __init__(self, timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT):
        self.session: aiohttp.ClientSession | None = None
        self.timeout = timeout

    async def __aenter__(self) -> "Request":
        self.session = aiohttp.ClientSession(headers=HEADERS, timeout=self.timeout)
        return self

    async def __aexit__(self, *args) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def get(self, url: str) -> dict | None:
        if self.session is None:
            raise RuntimeError(
                "Request must be used as an async context manager: "
                "`async with Request() as req:`"
            )
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.get(url) as res:
                    if res.status != 200:
                        body = await res.text()
                        raise APIError(
                            f"HTTP {res.status} for {url}",
                            status=res.status,
                            url=url,
                        )
                    text = await res.text()
                    return extract_json(text)

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
                    continue
                raise NetworkError(
                    f"Request failed after {MAX_RETRIES} attempts: {url}",
                ) from exc

        return None  # unreachable


async def safe_get(client, url: str, fallback=None):
    """Fetch via shared client or a fresh Request session.

    Returns ``fallback`` on any error.  Used by all API modules so they
    don't have to repeat the try/except boilerplate.
    """
    try:
        if client is not None:
            data = await client.get(url)
        else:
            async with Request() as req:
                data = await req.get(url)
        return data if data is not None else fallback
    except (APIError, NetworkError):
        return fallback
