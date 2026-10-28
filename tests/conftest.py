import asyncio
from collections.abc import AsyncIterator, Callable

import pytest
from aiohttp import web


@pytest.fixture
async def aiohttp_server() -> AsyncIterator[Callable[[web.Application], object]]:
    runners: list[web.AppRunner] = []

    async def factory(app: web.Application):
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        runners.append(runner)
        port = site._server.sockets[0].getsockname()[1]

        class Server:
            @staticmethod
            def make_url(path: str) -> str:
                return f"http://127.0.0.1:{port}{path}"

        return Server()

    yield factory
    await asyncio.gather(*(runner.cleanup() for runner in runners))
