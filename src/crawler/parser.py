"""HTML parsers for Hacker News pages."""

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from crawler.models import Story


def parse_stories(html: str, base_url: str) -> list[Story]:
    """Extract stories from a Hacker News listing page."""
    soup = BeautifulSoup(html, "html.parser")
    stories: list[Story] = []
    for row in soup.select("tr.athing"):
        story_id = row.get("id")
        title_link = row.select_one("span.titleline > a")
        if not story_id or title_link is None:
            continue
        subtext = row.find_next_sibling("tr")
        score_node = subtext.select_one("span.score") if subtext else None
        author_node = subtext.select_one("a.hnuser") if subtext else None
        score = _parse_score(score_node.get_text()) if score_node else None
        stories.append(
            Story(
                story_id=str(story_id),
                title=title_link.get_text(" ", strip=True),
                url=urljoin(base_url, title_link.get("href", "")),
                discussion_url=urljoin(base_url, f"item?id={story_id}"),
                score=score,
                author=author_node.get_text(strip=True) if author_node else None,
            )
        )
    return stories


def parse_discussion_links(html: str, base_url: str) -> list[str]:
    """Return unique HTTP links from a story discussion, preserving order."""
    soup = BeautifulSoup(html, "html.parser")
    result: list[str] = []
    seen: set[str] = set()
    selectors = ".toptext a[href], .comment a[href]"
    for anchor in soup.select(selectors):
        url = urljoin(base_url, anchor.get("href", ""))
        if urlparse(url).scheme not in {"http", "https"} or url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def _parse_score(value: str) -> int | None:
    try:
        return int(value.split(maxsplit=1)[0])
    except (ValueError, IndexError):
        return None
