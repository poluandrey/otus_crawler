from crawler.parser import parse_discussion_links, parse_stories


def test_parse_stories() -> None:
    html = """
    <table>
      <tr class="athing" id="42"><td>
        <span class="titleline"><a href="https://example.com/a">Title</a></span>
      </td></tr>
      <tr><td class="subtext"><span class="score">123 points</span>
        <a class="hnuser">alice</a></td></tr>
    </table>
    """
    stories = parse_stories(html, "https://news.ycombinator.com/")
    assert len(stories) == 1
    assert stories[0].story_id == "42"
    assert stories[0].score == 123
    assert stories[0].author == "alice"


def test_parse_discussion_links_deduplicates_and_filters() -> None:
    html = """
    <div class="toptext"><a href="https://example.com/a">a</a></div>
    <div class="comment"><a href="/item?id=1">internal</a>
      <a href="https://example.com/a">duplicate</a>
      <a href="mailto:a@example.com">mail</a></div>
    """
    assert parse_discussion_links(html, "https://news.ycombinator.com/") == [
        "https://example.com/a",
        "https://news.ycombinator.com/item?id=1",
    ]
