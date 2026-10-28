import json

from aiohttp import web

from crawler import Crawler, CrawlerConfig


async def test_run_once_saves_story_and_pages(aiohttp_server, tmp_path) -> None:
    async def index(request: web.Request) -> web.Response:
        base = f"{request.scheme}://{request.host}"
        return web.Response(
            text=f"""
        <table><tr class="athing" id="1"><td><span class="titleline">
        <a href="{base}/article">Article</a></span></td></tr>
        <tr><td class="subtext"><span class="score">5 points</span>
        <a class="hnuser">bob</a></td></tr></table>
        """,
            content_type="text/html",
        )

    async def discussion(request: web.Request) -> web.Response:
        base = f"{request.scheme}://{request.host}"
        return web.Response(
            text=f"<div class='comment'><a href='{base}/linked'>x</a></div>"
        )

    async def page(request: web.Request) -> web.Response:
        return web.Response(text="saved")

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/item", discussion)
    app.router.add_get("/article", page)
    app.router.add_get("/linked", page)
    server = await aiohttp_server(app)
    crawler = Crawler(
        CrawlerConfig(base_url=str(server.make_url("/")), output=tmp_path)
    )

    assert await crawler.run_once() == 1
    story = json.loads((tmp_path / "stories" / "1.json").read_text())
    assert story["title"] == "Article"
    assert len(story["links"]) == 2
    assert len(list((tmp_path / "pages").glob("*.bin"))) == 2
