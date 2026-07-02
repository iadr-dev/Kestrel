"""Live integration test for the daily_scoring cron job.

Runs ingest → scoring against a temp DuckDB and asserts scores land in
stock_scores. Verifies the C5 fix: with theme memberships loaded from the
correct data dir, theme scores are not uniformly the neutral fallback (50).

Run: pytest tests/cron/test_daily_scoring.py -v
"""

import pytest

from app.core.config import Settings
from app.providers.finmind.provider import FinMindProvider
from scripts.daily_ingest import ingest_institutional, ingest_prices, ingest_revenue
from scripts.daily_scoring import run_daily_scoring

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def provider():
    p = FinMindProvider(Settings())
    await p.initialize()
    yield p
    await p.close()


@pytest.fixture
async def ingested_db(provider, isolated_duckdb, last_trading_day):
    """Populate the temp DuckDB with real price/institutional/revenue data."""
    await ingest_prices(provider, last_trading_day)
    await ingest_institutional(provider, last_trading_day)
    await ingest_revenue(provider, last_trading_day)
    return isolated_duckdb


class TestDailyScoring:
    async def test_scores_persisted(self, ingested_db):
        results = await run_daily_scoring(top_n=30)
        assert len(results) > 0

        count = ingested_db._query_one_sync("SELECT COUNT(*) FROM stock_scores", None)[0]
        assert count == len(results)

    async def test_scores_in_valid_range(self, ingested_db):
        results = await run_daily_scoring(top_n=30)
        for r in results:
            for factor in ("technical_score", "chip_score", "fundamental_score", "theme_score", "overall_score"):
                assert 0 <= r[factor] <= 100, f"{factor}={r[factor]} out of range for {r['stock_id']}"

    async def test_theme_scores_not_all_neutral(self, ingested_db):
        """C5 guard: if theme memberships load correctly, theme scores vary.

        The pre-fix bug made _load_theme_memberships() read a non-existent path,
        so every stock got the neutral fallback (50). Real membership data should
        produce at least some non-50 theme scores across 30 stocks.
        """
        results = await run_daily_scoring(top_n=30)
        theme_scores = {r["theme_score"] for r in results}
        assert theme_scores != {50}, "all theme scores are neutral — theme memberships likely not loading"
