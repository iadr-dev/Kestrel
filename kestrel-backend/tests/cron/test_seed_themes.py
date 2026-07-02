"""Live integration test for the seed_themes cron job.

Seeds themes/memberships/tiers into a temp DuckDB from FinMind's
TaiwanStockIndustryChain (via the backend provider layer), then verifies the
data is queryable through ThemeRepository the way the API reads it.

Run: pytest tests/cron/test_seed_themes.py -v
"""

import pytest

from app.services.data.theme_repository import ThemeRepository
from scripts.seed_themes import seed_from_industry_chain, seed_tiers

pytestmark = pytest.mark.asyncio


class TestSeedThemes:
    async def test_industry_chain_seed_populates_themes(self, isolated_duckdb):
        result = await seed_from_industry_chain()
        assert result["themes"] > 0, "FinMind industry chain should yield themes"
        assert result["memberships"] > result["themes"]

        repo = ThemeRepository(db=isolated_duckdb)
        themes = await repo.list_themes()
        assert len(themes) == result["themes"]
        # Every theme should report a positive stock count.
        assert all(t["stock_count"] > 0 for t in themes)

    async def test_tsmc_mapped_to_a_theme(self, isolated_duckdb):
        """TSMC (2330) must land in some semiconductor-ish theme."""
        await seed_from_industry_chain()
        rows = isolated_duckdb._query_sync(
            "SELECT theme_id FROM theme_memberships WHERE stock_id = '2330'", None
        )
        assert len(rows) >= 1

    async def test_tiers_seeded_and_grouped(self, isolated_duckdb):
        await seed_from_industry_chain()
        n = seed_tiers()
        assert n > 0

        # A theme that has tier mappings should expose non-empty buckets.
        repo = ThemeRepository(db=isolated_duckdb)
        tiers = await repo.get_theme_tiers("半導體")
        if tiers["tier_defined"]:
            buckets = tiers["data"]
            total = sum(len(buckets[k]) for k in ("upstream", "midstream", "downstream"))
            assert total > 0
