"""Live HTTP-route tests for the /api/v1/stocks router.

Unlike the provider-direct tests in tests/endpoint/finmind/, these drive the
REAL FastAPI routes through the ASGI app (with lifespan, so app.state providers
+ DuckDB + cache are wired exactly as in production). This is what catches
regressions in the endpoint layer itself: DI wiring, response envelope,
pagination params, status codes.

Uses real FinMind keys from .env. FinMind intermittently rate-limits / drops
connections; the backend correctly surfaces that as a 503 ProviderUnavailable
envelope, so live-backed endpoints accept either 200 (data) or 503 (upstream
down) — both prove the route works. Validation/pagination assertions don't touch
the upstream and stay strict.

Run: pytest tests/endpoint/finmind/test_stocks_routes.py -v
"""

from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

TSMC = "2330"
# A window safely in the past so the market data is settled.
START = (date.today() - timedelta(days=14)).isoformat()
ONE_DAY = (date.today() - timedelta(days=7)).isoformat()


def _assert_list_envelope(body: dict) -> None:
    """Every /stocks route returns the DataListResponse shape."""
    assert "data" in body
    assert "count" in body
    assert isinstance(body["data"], list)
    assert body["count"] == len(body["data"])


def _assert_live_ok(resp) -> dict | None:
    """Assert a live FinMind-backed endpoint behaves correctly.

    Returns EITHER 200 with the DataListResponse envelope, OR 503 with the
    unified error envelope when FinMind is unavailable. Both prove route + DI +
    error handling work. Returns the 200 body (or None on 503).
    """
    if resp.status_code == 503:
        body = resp.json()
        assert body["error"]["code"] in (
            "PROVIDER_UNAVAILABLE", "PROVIDER_RATE_LIMITED", "PROVIDER_ERROR",
        )
        return None
    assert resp.status_code == 200, f"unexpected {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    _assert_list_envelope(body)
    return body


class TestStockPrice:
    async def test_price_ok(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price", params={"start_date": START})
        _assert_live_ok(r)

    async def test_price_missing_required_start_date_422(self, live_client):
        """start_date is required → unified validation envelope, status 422."""
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price")
        assert r.status_code == 422
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"

    async def test_price_with_indicators(self, live_client):
        r = await live_client.get(
            f"/api/v1/stocks/{TSMC}/price",
            params={"start_date": START, "indicators": ["sma", "rsi"]},
        )
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            assert "data" in r.json()

    async def test_adjusted_price(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price/adjusted", params={"start_date": START})
        _assert_live_ok(r)

    async def test_price_tick(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price/tick", params={"trade_date": ONE_DAY})
        _assert_live_ok(r)

    async def test_price_kbar(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price/kbar", params={"trade_date": ONE_DAY})
        _assert_live_ok(r)

    async def test_week_price(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price/week", params={"start_date": START})
        _assert_live_ok(r)

    async def test_month_price(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/price/month", params={"start_date": START})
        _assert_live_ok(r)


class TestStockInfo:
    async def test_info_all(self, live_client):
        """stock_info is cached (24h TTL) so this is reliably 200 with full data."""
        r = await live_client.get("/api/v1/stocks/info/all")
        body = _assert_live_ok(r)
        if body is not None:
            assert "total" in body  # pagination field added in the audit

    async def test_info_all_pagination(self, live_client):
        """limit/offset return a page; total reflects the full count."""
        r = await live_client.get("/api/v1/stocks/info/all", params={"limit": 10, "offset": 5})
        body = _assert_live_ok(r)
        if body is not None and body["total"] >= 15:
            assert body["count"] == 10
            assert body["total"] > body["count"]

    async def test_info_all_limit_validation(self, live_client):
        """limit above the cap is rejected with the validation envelope (no upstream call)."""
        r = await live_client.get("/api/v1/stocks/info/all", params={"limit": 999999})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_single_stock_info(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/info")
        body = _assert_live_ok(r)
        if body and body["count"]:
            assert body["data"][0]["stock_id"] == TSMC

    async def test_per(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/per", params={"start_date": START})
        _assert_live_ok(r)


class TestSnapshot:
    async def test_single_snapshot(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/snapshot")
        _assert_live_ok(r)

    async def test_snapshot_all(self, live_client):
        r = await live_client.get("/api/v1/stocks/snapshot/all")
        body = _assert_live_ok(r)
        if body is not None:
            assert "total" in body

    async def test_snapshot_all_pagination(self, live_client):
        r = await live_client.get("/api/v1/stocks/snapshot/all", params={"limit": 5})
        body = _assert_live_ok(r)
        if body is not None:
            assert body["count"] <= 5
            assert "total" in body


class TestMisc:
    async def test_trading_dates(self, live_client):
        r = await live_client.get("/api/v1/stocks/trading-dates")
        _assert_live_ok(r)

    async def test_price_limits(self, live_client):
        r = await live_client.get("/api/v1/stocks/price-limits", params={"start_date": ONE_DAY})
        _assert_live_ok(r)

    async def test_day_trading(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/day-trading/{TSMC}", params={"start_date": START})
        _assert_live_ok(r)

    async def test_suspended(self, live_client):
        r = await live_client.get("/api/v1/stocks/suspended", params={"start_date": START})
        _assert_live_ok(r)

    async def test_10_year(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/10-year/{TSMC}", params={"start_date": START})
        _assert_live_ok(r)

    async def test_market_news(self, live_client):
        r = await live_client.get("/api/v1/stocks/news/market")
        _assert_live_ok(r)

    async def test_stock_news(self, live_client):
        r = await live_client.get(f"/api/v1/stocks/{TSMC}/news")
        _assert_live_ok(r)
