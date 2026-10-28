"""Domain objects used by the crawler."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Story:
    """A story shown on a Hacker News listing page."""

    story_id: str
    title: str
    url: str
    discussion_url: str
    score: int | None = None
    author: str | None = None
    links: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return asdict(self)
