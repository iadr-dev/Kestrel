"""Live tests for PTT board scraper.

Source: https://www.ptt.cc/bbs/{board}/index.html
Provides: board post listings and full post content

Run: pytest tests/scraper/test_ptt.py -v
"""

import pytest

from app.scrapers.ptt import BOARDS, run, scrape_board, scrape_post_content


class TestScrapeBoard:
    @pytest.mark.asyncio
    async def test_stock_board(self):
        """Stock board returns posts (empty if PTT blocks connection)."""
        data = await scrape_board("Stock", pages=1)
        assert isinstance(data, list)
        if not data:
            pytest.skip("PTT connection blocked from this environment")
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_post_fields(self):
        """Each post has expected fields."""
        data = await scrape_board("Stock", pages=1)
        if not data:
            pytest.skip("PTT connection blocked from this environment")
        post = data[0]
        assert "title" in post
        assert "author" in post
        assert "link" in post
        assert "push_count" in post
        assert "board" in post
        assert post["board"] == "Stock"

    @pytest.mark.asyncio
    async def test_link_is_full_url(self):
        """Link should be a full PTT URL."""
        data = await scrape_board("Stock", pages=1)
        if data:
            link = data[0]["link"]
            assert link.startswith("https://www.ptt.cc/bbs/")

    @pytest.mark.asyncio
    async def test_multiple_pages(self):
        """Fetching 2 pages returns more posts than 1."""
        one_page = await scrape_board("Stock", pages=1)
        two_pages = await scrape_board("Stock", pages=2)
        if one_page and two_pages:
            assert len(two_pages) > len(one_page)

    @pytest.mark.asyncio
    async def test_tag_extraction(self):
        """Tags like [標的] [新聞] are extracted."""
        data = await scrape_board("Stock", pages=1)
        tagged = [p for p in data if p.get("tag")]
        # Most Stock board posts have tags
        assert len(tagged) > 0

    @pytest.mark.asyncio
    async def test_invalid_board_returns_empty(self):
        """Non-existent board returns empty."""
        data = await scrape_board("NonExistentBoard12345", pages=1)
        assert isinstance(data, list)
        assert len(data) == 0


class TestScrapePostContent:
    @pytest.mark.asyncio
    async def test_fetch_real_post(self):
        """Fetch a real post from Stock board."""
        posts = await scrape_board("Stock", pages=1)
        if not posts:
            pytest.skip("No posts available")
        url = posts[0]["link"]
        content = await scrape_post_content(url)
        assert content is not None
        assert "title" in content
        assert "body" in content
        assert "author" in content
        assert len(content["body"]) > 0

    @pytest.mark.asyncio
    async def test_has_push_info(self):
        """Post content includes push/comment data."""
        posts = await scrape_board("Stock", pages=1)
        if not posts:
            pytest.skip("No posts available")
        url = posts[0]["link"]
        content = await scrape_post_content(url)
        if content:
            assert "pushes" in content
            assert "push_count" in content
            assert isinstance(content["pushes"], list)

    @pytest.mark.asyncio
    async def test_invalid_url_returns_none(self):
        """Non-existent post URL returns None."""
        content = await scrape_post_content("https://www.ptt.cc/bbs/Stock/M.9999999999.A.000.html")
        assert content is None


class TestBoardsConstant:
    def test_boards_mapping_exists(self):
        """BOARDS dict maps lowercase keys to proper board names."""
        assert "stock" in BOARDS
        assert BOARDS["stock"] == "Stock"


class TestRun:
    @pytest.mark.asyncio
    async def test_run_returns_scrape_result(self):
        result = await run(boards=["Stock"], pages=1)
        assert result.source == "ptt"
        assert result.rows_written > 0
        assert result.duration_ms > 0
