"""Live tests for scraper HTTP endpoints (/api/v1/scrapers/*).

Tests the actual FastAPI endpoints end-to-end via TestClient.
Covers: /chip-concentration, /rss, /ptt/{board}, /ptt/{board}/post

Run: pytest tests/endpoint/scraper/ -v
"""

import pytest


class TestChipConcentrationEndpoint:
    """Test GET /api/v1/scrapers/chip-concentration/{stock_id}"""

    @pytest.mark.asyncio
    async def test_tsmc_returns_200(self, client):
        resp = await client.get("/api/v1/scrapers/chip-concentration/2330")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "count" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_has_chip_fields(self, client):
        resp = await client.get("/api/v1/scrapers/chip-concentration/2330")
        body = resp.json()
        if body["count"] > 0:
            row = body["data"][0]
            assert "stock_id" in row
            assert "chip_concentration" in row
            assert "foreign_pct" in row

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        resp = await client.get("/api/v1/scrapers/chip-concentration/9999")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0


class TestRssEndpoint:
    """Test GET /api/v1/scrapers/rss"""

    @pytest.mark.asyncio
    async def test_default_feeds(self, client):
        """No params returns aggregated feeds."""
        resp = await client.get("/api/v1/scrapers/rss")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "count" in body
        assert isinstance(body["data"], list)
        assert body["count"] > 0

    @pytest.mark.asyncio
    async def test_article_fields(self, client):
        """Articles have title, link, source, date."""
        resp = await client.get("/api/v1/scrapers/rss")
        body = resp.json()
        if body["count"] > 0:
            article = body["data"][0]
            assert "title" in article
            assert "link" in article
            assert "source" in article
            assert "date" in article

    @pytest.mark.asyncio
    async def test_custom_feed_url(self, client):
        """Custom feed_url param works."""
        resp = await client.get("/api/v1/scrapers/rss", params={"feed_url": "https://technews.tw/feed/"})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_invalid_feed_url_returns_empty(self, client):
        """Bad URL returns empty gracefully."""
        resp = await client.get("/api/v1/scrapers/rss", params={"feed_url": "https://example.com/no-feed"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0


class TestPttBoardEndpoint:
    """Test GET /api/v1/scrapers/ptt/{board}"""

    @pytest.mark.asyncio
    async def test_stock_board(self, client):
        """Stock board returns posts or empty (if PTT blocks)."""
        resp = await client.get("/api/v1/scrapers/ptt/stock", params={"pages": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    @pytest.mark.asyncio
    async def test_post_fields(self, client):
        """Posts have expected fields."""
        resp = await client.get("/api/v1/scrapers/ptt/stock", params={"pages": 1})
        body = resp.json()
        if body["count"] > 0:
            post = body["data"][0]
            assert "title" in post
            assert "author" in post
            assert "link" in post
            assert "board" in post

    @pytest.mark.asyncio
    async def test_invalid_board_returns_empty(self, client):
        """Non-existent board returns empty."""
        resp = await client.get("/api/v1/scrapers/ptt/nonexistent_board_xyz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0

    @pytest.mark.asyncio
    async def test_pages_param_validation(self, client):
        """Pages must be 1-5."""
        resp = await client.get("/api/v1/scrapers/ptt/stock", params={"pages": 10})
        assert resp.status_code == 422


class TestPttPostEndpoint:
    """Test GET /api/v1/scrapers/ptt/{board}/post"""

    @pytest.mark.asyncio
    async def test_invalid_url_returns_error(self, client):
        """Non-existent post URL returns error."""
        resp = await client.get(
            "/api/v1/scrapers/ptt/stock/post",
            params={"url": "https://www.ptt.cc/bbs/Stock/M.9999999999.A.000.html"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] is None or "error" in body

    @pytest.mark.asyncio
    async def test_requires_url_param(self, client):
        """Missing url param returns 422."""
        resp = await client.get("/api/v1/scrapers/ptt/stock/post")
        assert resp.status_code == 422
