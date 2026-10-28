"""Persistent filesystem storage."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from crawler.models import Story


class Storage:
    """Store story metadata and downloaded pages on disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.stories_dir = root / "stories"
        self.pages_dir = root / "pages"

    async def prepare(self) -> None:
        """Create output directories."""
        await asyncio.to_thread(self.stories_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(self.pages_dir.mkdir, parents=True, exist_ok=True)

    async def save_story(self, story: Story) -> Path:
        """Atomically save story metadata as JSON."""
        payload = story.to_dict()
        payload["crawled_at"] = datetime.now(UTC).isoformat()
        path = self.stories_dir / f"{story.story_id}.json"
        await asyncio.to_thread(
            _atomic_write_text, path, json.dumps(payload, ensure_ascii=False, indent=2)
        )
        return path

    def page_path(self, url: str) -> Path:
        """Map a URL to a stable content filename."""
        digest = hashlib.sha256(url.encode()).hexdigest()
        return self.pages_dir / f"{digest}.bin"

    async def has_page(self, url: str) -> bool:
        """Check whether a URL was downloaded in a previous run."""
        return await asyncio.to_thread(self.page_path(url).exists)

    async def save_page(self, url: str, content: bytes, content_type: str) -> Path:
        """Save response bytes and companion metadata atomically."""
        path = self.page_path(url)
        metadata = path.with_suffix(".json")
        await asyncio.gather(
            asyncio.to_thread(_atomic_write_bytes, path, content),
            asyncio.to_thread(
                _atomic_write_text,
                metadata,
                json.dumps(
                    {"url": url, "content_type": content_type},
                    ensure_ascii=False,
                    indent=2,
                ),
            ),
        )
        return path


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
