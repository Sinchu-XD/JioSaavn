import aiohttp
import json
from .Parser import extract_json

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


class Request:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=HEADERS)
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get(self, url):
        try:
            async with self.session.get(url, timeout=10) as res:
                text = await res.text()
                raw = extract_json(text)

                if not raw:
                    return None

                return json.loads(raw)

        except Exception:
            return None
