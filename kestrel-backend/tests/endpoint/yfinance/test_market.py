"""Live tests for yfinance market module.

Covers: get_sector, get_industry, get_market_summary,
        get_earnings_calendar, get_splits_calendar, get_ipo_calendar,
        get_economic_events

Run: pytest tests/endpoint/yfinance/test_market.py -v
"""

import pytest


class TestGetSector:
    @pytest.mark.asyncio
    async def test_technology_sector(self, yf):
        data = await yf.get_sector("technology")
        assert data.get("sector_key") == "technology" or "error" in data

    @pytest.mark.asyncio
    async def test_returns_top_companies(self, yf):
        data = await yf.get_sector("technology")
        if "error" not in data:
            assert "top_companies" in data
            assert len(data["top_companies"]) > 0

    @pytest.mark.asyncio
    async def test_returns_industries(self, yf):
        data = await yf.get_sector("technology")
        if "error" not in data:
            assert "industries" in data


class TestGetIndustry:
    @pytest.mark.asyncio
    async def test_semiconductors(self, yf):
        data = await yf.get_industry("semiconductors")
        assert data.get("industry_key") == "semiconductors" or "error" in data

    @pytest.mark.asyncio
    async def test_returns_top_companies(self, yf):
        data = await yf.get_industry("semiconductors")
        if "error" not in data:
            assert "top_companies" in data
            assert len(data["top_companies"]) > 0

    @pytest.mark.asyncio
    async def test_has_sector_reference(self, yf):
        data = await yf.get_industry("semiconductors")
        if "error" not in data:
            assert "sector_key" in data or "sector_name" in data


class TestGetMarketSummary:
    @pytest.mark.asyncio
    async def test_us_market(self, yf):
        data = await yf.get_market_summary("US")
        assert data["market"] == "US"
        assert "status" in data or "summary" in data

    @pytest.mark.asyncio
    async def test_invalid_market_returns_error(self, yf):
        data = await yf.get_market_summary("INVALID_MARKET_XYZ")
        assert "error" in data or data.get("status") == {}


class TestGetEarningsCalendar:
    @pytest.mark.asyncio
    async def test_returns_upcoming_earnings(self, yf):
        data = await yf.get_earnings_calendar()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_with_date_range(self, yf):
        from datetime import date, timedelta
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=3)).isoformat()
        data = await yf.get_earnings_calendar(start, end)
        assert isinstance(data, list)


class TestGetSplitsCalendar:
    @pytest.mark.asyncio
    async def test_returns_list(self, yf):
        data = await yf.get_splits_calendar()
        assert isinstance(data, list)


class TestGetIpoCalendar:
    @pytest.mark.asyncio
    async def test_returns_list(self, yf):
        data = await yf.get_ipo_calendar()
        assert isinstance(data, list)


class TestGetEconomicEvents:
    @pytest.mark.asyncio
    async def test_returns_list(self, yf):
        data = await yf.get_economic_events()
        assert isinstance(data, list)
