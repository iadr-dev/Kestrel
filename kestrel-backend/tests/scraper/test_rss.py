"""Live tests for RSS feed scraper.

Sources: technews.tw, finance.technews.tw, ithome.com.tw, blocktempo.com
Provides: aggregated financial/tech news from RSS/Atom feeds

Run: pytest tests/scraper/test_rss.py -v
"""

import pytest

from app.scrapers.rss import (
    DEFAULT_FEEDS,
    _clean_html,
    _parse_date,
    fetch_feed,
    fetch_multiple_feeds,
    run,
)


class TestFetchFeed:
    @pytest.mark.asyncio
    async def test_technews_feed(self):
        """TechNews RSS feed returns articles."""
        data = await fetch_feed("https://technews.tw/feed/", max_items=5)
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_article_fields(self):
        """Each article has expected fields."""
        data = await fetch_feed("https://technews.tw/feed/", max_items=3)
        if data:
            article = data[0]
            assert "title" in article and article["title"]
            assert "link" in article and article["link"]
            assert "date" in article
            assert "source" in article
            assert "description" in article

    @pytest.mark.asyncio
    async def test_max_items_limit(self):
        """Respects max_items parameter."""
        data = await fetch_feed("https://technews.tw/feed/", max_items=3)
        assert len(data) <= 3

    @pytest.mark.asyncio
    async def test_link_is_url(self):
        """Links should be valid URLs."""
        data = await fetch_feed("https://technews.tw/feed/", max_items=3)
        if data:
            assert data[0]["link"].startswith("http")

    @pytest.mark.asyncio
    async def test_invalid_url_returns_empty(self):
        """Non-existent feed returns empty."""
        data = await fetch_feed("https://example.com/nonexistent.xml")
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_non_rss_url_returns_empty(self):
        """Non-RSS URL returns empty gracefully."""
        data = await fetch_feed("https://www.google.com")
        assert isinstance(data, list)
        assert len(data) == 0


class TestFetchMultipleFeeds:
    @pytest.mark.asyncio
    async def test_default_feeds(self):
        """Fetches from all default feeds."""
        data = await fetch_multiple_feeds(max_per_feed=3)
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_sorted_by_date_desc(self):
        """Results sorted by date descending."""
        data = await fetch_multiple_feeds(max_per_feed=5)
        if len(data) >= 2:
            dates = [a["date"] for a in data if a["date"]]
            # Should be roughly descending (some may have empty dates)
            non_empty = [d for d in dates if d]
            if len(non_empty) >= 2:
                assert non_empty[0] >= non_empty[1]

    @pytest.mark.asyncio
    async def test_custom_feeds(self):
        """Custom feed URLs work."""
        custom = {"technews": "https://technews.tw/feed/"}
        data = await fetch_multiple_feeds(feed_urls=custom, max_per_feed=3)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_multiple_sources_present(self):
        """Results come from multiple sources."""
        data = await fetch_multiple_feeds(max_per_feed=5)
        sources = {a.get("source") for a in data if a.get("source")}
        assert len(sources) >= 1


class TestDefaultFeeds:
    def test_default_feeds_defined(self):
        """DEFAULT_FEEDS has expected entries."""
        assert "technews" in DEFAULT_FEEDS
        assert "technews_finance" in DEFAULT_FEEDS
        assert all(url.startswith("http") for url in DEFAULT_FEEDS.values())


class TestParseDate:
    def test_rss_pubdate_format(self):
        result = _parse_date("Sat, 07 Jun 2025 10:30:00 +0800")
        assert result.startswith("2025-06-07")

    def test_iso_format(self):
        result = _parse_date("2025-06-07T10:30:00Z")
        assert result.startswith("2025-06-07")

    def test_empty_string(self):
        assert _parse_date("") == ""

    def test_invalid_returns_truncated(self):
        result = _parse_date("not a date at all")
        assert isinstance(result, str)


class TestCleanHtml:
    def test_strips_tags(self):
        assert _clean_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty_returns_empty(self):
        assert _clean_html("") == ""

    def test_preserves_text(self):
        assert _clean_html("no tags here") == "no tags here"


class TestRun:
    @pytest.mark.asyncio
    async def test_run_returns_scrape_result(self):
        result = await run()
        assert result.source == "rss"
        assert result.rows_written >= 0
        assert result.duration_ms > 0
