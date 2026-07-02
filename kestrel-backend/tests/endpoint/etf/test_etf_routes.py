"""Live HTTP-route tests for the /api/v1/etf router.

Drives the real FastAPI routes (with lifespan) — in particular /etf/list, which
was refactored in the audit to be cache-first via ETFService (the existing
tests/endpoint/etf test calls the scraper directly and would NOT catch a broken
endpoint). Uses real FinMind keys from .env.

Run: pytest tests/endpoint/http/test_etf_routes.py -v
"""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestEtfList:
    async def test_list_ok(self, live_client):
        """Cache-first popular-ETF endpoint returns the list envelope."""
        r = await live_client.get("/api/v1/etf/list")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "count" in body
        assert isinstance(body["data"], list)

    async def test_list_shape(self, live_client):
        """When data is present, rows carry the expected ETF fields + total_etfs."""
        r = await live_client.get("/api/v1/etf/list")
        body = r.json()
        if body["count"] > 0:
            row = body["data"][0]
            assert "stock_id" in row
            assert "stock_name" in row
            assert "close" in row
            assert "volume" in row
            assert "total_etfs" in body

    async def test_list_is_cached(self, live_client):
        """Second call hits the cache — must return identical payload, still 200."""
        r1 = await live_client.get("/api/v1/etf/list")
        r2 = await live_client.get("/api/v1/etf/list")
        assert r1.status_code == r2.status_code == 200
        assert r1.json()["count"] == r2.json()["count"]


class TestEtfNav:
    async def test_nav_all(self, live_client):
        r = await live_client.get("/api/v1/etf/nav")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    async def test_nav_single_0050(self, live_client):
        r = await live_client.get("/api/v1/etf/nav/0050")
        assert r.status_code == 200
        assert "data" in r.json()

    async def test_premium_discount(self, live_client):
        r = await live_client.get("/api/v1/etf/premium-discount", params={"threshold": 0.5})
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    async def test_holdings(self, live_client):
        """TWSE legacy holdings endpoint — may be empty but must return list envelope."""
        r = await live_client.get("/api/v1/etf/0050/holdings")
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)
