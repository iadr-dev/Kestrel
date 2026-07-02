"""Live integration tests for the scrape_profiles cron job.

Profiles feed extract_supply_chain, so the shapes must match what that consumer
reads (name_zh / main_business / industry for TW; long fields for US).

Run: pytest tests/cron/test_scrape_profiles.py -v
"""

import pytest

from app.providers.yfinance.provider import YFinanceProvider
from app.scrapers.mops_profile import MOPSProfileScraper

pytestmark = pytest.mark.asyncio


class TestTWProfiles:
    async def test_mops_profile_shape(self):
        scraper = MOPSProfileScraper()
        profile = await scraper.get_company_info("2330")
        if profile.get("error"):
            pytest.skip(f"MOPS unreachable from this environment: {profile.get('error')}")
        assert profile.get("stock_id") == "2330"
        # extract_supply_chain reads these keys — guard their presence.
        assert any(k in profile for k in ("name_zh", "company_name", "industry"))


class TestUSProfiles:
    async def test_yfinance_profile_shape(self):
        provider = YFinanceProvider()
        profile = await provider.get_info("NVDA")
        if profile.get("error"):
            pytest.skip(f"yfinance unreachable: {profile.get('error')}")
        assert profile  # non-empty dict
        # yfinance returns a long business summary / sector for supply-chain extraction.
        assert any(k in profile for k in ("longBusinessSummary", "sector", "industry", "shortName"))
