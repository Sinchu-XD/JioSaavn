from .Request import Request


class JioSaavnClient:
    def __init__(self):
        self._req = Request()

    async def __aenter__(self):
        await self._req.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self._req.__aexit__(*args)

    async def get(self, url):
        return await self._req.get(url)
