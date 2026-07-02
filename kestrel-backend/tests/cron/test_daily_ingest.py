"""Live integration tests for the daily_ingest cron job.

Runs the real FinMind-backed ingest into a temp DuckDB and asserts the data
lands in the tables the scoring pipeline reads. Notably verifies the C6 fix:
institutional data must be PER-STOCK (queryable by real stock_id), not collapsed
to a single market-wide 'TOTAL' row.

Run: pytest tests/cron/test_daily_ingest.py -v
"""

import pytest

from app.core.config import Settings
from app.providers.finmind.provider import FinMindProvider
from scripts.daily_ingest import (
    ingest_institutional,
    ingest_prices,
    ingest_revenue,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def provider():
    p = FinMindProvider(Settings())
    await p.initialize()
    yield p
    await p.close()


class TestDailyIngestPrices:
    async def test_prices_ingested_into_price_daily(self, provider, isolated_duckdb, last_trading_day):
        count = await ingest_prices(provider, last_trading_day)
        assert count > 0, "expected at least some prices for a recent trading day"

        rows = isolated_duckdb._query_sync("SELECT COUNT(*) FROM price_daily", None)
        assert rows[0][0] == count

    async def test_price_rows_have_ohlc(self, provider, isolated_duckdb, last_trading_day):
        await ingest_prices(provider, last_trading_day)
        row = isolated_duckdb._query_one_sync(
            "SELECT stock_id, open, high, low, close FROM price_daily WHERE close > 0 LIMIT 1", None
        )
        assert row is not None
        stock_id, o, h, low, c = row
        assert stock_id
        assert h >= low  # high never below low


class TestDailyIngestInstitutional:
    """C6 regression guard: institutional data must be per-stock, not 'TOTAL'."""

    async def test_institutional_is_per_stock(self, provider, isolated_duckdb, last_trading_day):
        count = await ingest_institutional(provider, last_trading_day)
        assert count > 0, "expected per-stock institutional rows"

        # The bug collapsed everything to stock_id='TOTAL'. Assert we have many
        # distinct real stock ids instead.
        distinct = isolated_duckdb._query_one_sync(
            "SELECT COUNT(DISTINCT stock_id) FROM institutional_daily", None
        )[0]
        assert distinct > 10, f"expected many per-stock rows, got {distinct} distinct ids"

        total_rows = isolated_duckdb._query_one_sync(
            "SELECT COUNT(*) FROM institutional_daily WHERE stock_id = 'TOTAL'", None
        )[0]
        assert total_rows == 0, "institutional_daily should not contain a market-wide TOTAL row"

    async def test_chip_consumer_query_finds_tsmc(self, provider, isolated_duckdb, last_trading_day):
        """The chip score queries `WHERE stock_id IN (...)` — TSMC must be present."""
        await ingest_institutional(provider, last_trading_day)
        row = isolated_duckdb._query_one_sync(
            "SELECT stock_id, buy, sell FROM institutional_daily WHERE stock_id = '2330' LIMIT 1",
            None,
        )
        assert row is not None, "TSMC (2330) institutional row should be queryable by the chip score"


class TestDailyIngestRevenue:
    async def test_revenue_ingested(self, provider, isolated_duckdb, last_trading_day):
        count = await ingest_revenue(provider, last_trading_day)
        assert count > 0
        row = isolated_duckdb._query_one_sync(
            "SELECT stock_id, revenue FROM revenue_monthly LIMIT 1", None
        )
        assert row is not None
