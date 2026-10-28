"""Asynchronous crawler orchestration."""

import asyncio
import logging
import ssl
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import certifi

from crawler.parser import parse_discussion_links, parse_stories
from crawler.storage import Storage

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CrawlerConfig:
    """Runtime crawler settings."""

    base_url: str = "https://news.ycombinator.com/"
    interval: float = 60.0
    limit: int = 30
    concurrency: int = 10
    timeout: float = 20.0
    output: Path = Path("data")
    max_page_bytes: int = 10 * 1024 * 1024


class Crawler:
    """Periodically crawl Hacker News and linked pages."""

    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.storage = Storage(config.output)
        self._semaphore = asyncio.Semaphore(config.concurrency)

    async def run_once(self) -> int:
        """Run one crawl cycle and return the number of processed stories."""
        await self.storage.prepare()
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        headers = {"User-Agent": "otus-hn-crawler/1.0 (+educational project)"}
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(
            timeout=timeout, headers=headers, connector=connector
        ) as session:
            listing = await self._get_text(session, self.config.base_url)
            stories = parse_stories(listing, self.config.base_url)[: self.config.limit]
            results = await asyncio.gather(
                *(self._process_story(session, story) for story in stories),
                return_exceptions=True,
            )
        for result in results:
            if isinstance(result, Exception):
                LOGGER.error("Could not process story: %s", result)
        successful = sum(not isinstance(result, Exception) for result in results)
        LOGGER.info("Crawl finished: %d/%d stories processed", successful, len(stories))
        return successful

    async def run_forever(self) -> None:
        """Run crawl cycles at the configured interval until cancelled."""
        while True:
            started = asyncio.get_running_loop().time()
            try:
                await self.run_once()
            except (aiohttp.ClientError, TimeoutError) as error:
                LOGGER.error("Crawl cycle failed: %s", error)
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0, self.config.interval - elapsed))

    async def _process_story(
        self, session: aiohttp.ClientSession, story: object
    ) -> None:
        from crawler.models import Story

        if not isinstance(story, Story):
            raise TypeError("story must be a Story")
        discussion = await self._get_text(session, story.discussion_url)
        discussion_links = parse_discussion_links(discussion, self.config.base_url)
        candidates = [story.url, *discussion_links]
        story.links = list(dict.fromkeys(candidates))
        await asyncio.gather(
            *(self._download_page(session, url) for url in story.links)
        )
        await self.storage.save_story(story)
        LOGGER.info("Saved story %s (%d links)", story.story_id, len(story.links))

    async def _get_text(self, session: aiohttp.ClientSession, url: str) -> str:
        async with self._semaphore, session.get(url) as response:
            response.raise_for_status()
            return await response.text(errors="replace")

    async def _download_page(self, session: aiohttp.ClientSession, url: str) -> None:
        if await self.storage.has_page(url):
            return
        try:
            async with self._semaphore, session.get(url) as response:
                response.raise_for_status()
                length = response.content_length
                if length is not None and length > self.config.max_page_bytes:
                    LOGGER.warning("Skipping oversized response: %s", url)
                    return
                content = await response.content.read(self.config.max_page_bytes + 1)
                if len(content) > self.config.max_page_bytes:
                    LOGGER.warning("Skipping oversized response: %s", url)
                    return
                await self.storage.save_page(
                    str(response.url), content, response.headers.get("Content-Type", "")
                )
        except (aiohttp.ClientError, TimeoutError) as error:
            LOGGER.warning("Could not download %s: %s", url, error)
