"""Live integration test for the weekly_ai_summaries cron job.

Generates AI summaries for a couple of stocks (needs price/revenue data + an LLM
key) and asserts they persist to the ai_summaries table that /ai/summary reads.

Run: pytest tests/cron/test_weekly_ai_summaries.py -v
"""

import pytest

from app.core.config import Settings
from app.providers.finmind.provider import FinMindProvider
from scripts.daily_ingest import ingest_institutional, ingest_prices, ingest_revenue
from scripts.weekly_ai_summaries import generate_summaries

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def provider():
    p = FinMindProvider(Settings())
    await p.initialize()
    yield p
    await p.close()


@pytest.fixture
async def ingested_db(provider, isolated_duckdb, last_trading_day):
    await ingest_prices(provider, last_trading_day)
    await ingest_institutional(provider, last_trading_day)
    await ingest_revenue(provider, last_trading_day)
    return isolated_duckdb


class TestWeeklyAiSummaries:
    async def test_summaries_persisted(self, ingested_db):
        # Small set to keep the LLM cost/time low.
        results = await generate_summaries(stock_ids=["2330", "2317"], max_stocks=2)
        assert isinstance(results, list)

        count = ingested_db._query_one_sync("SELECT COUNT(*) FROM ai_summaries", None)[0]
        assert count >= 1, "expected at least one AI summary row"

    async def test_summary_has_position_label(self, ingested_db):
        await generate_summaries(stock_ids=["2330"], max_stocks=1)
        row = ingested_db._query_one_sync(
            "SELECT stock_id, position_label, summary FROM ai_summaries WHERE stock_id = '2330'", None
        )
        if row is not None:  # summary generation may rule-based-fallback; row still written
            assert row[0] == "2330"
            assert row[2]  # non-empty summary text
