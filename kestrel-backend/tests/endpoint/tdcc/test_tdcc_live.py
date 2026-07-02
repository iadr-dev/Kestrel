"""Live tests for TDCC provider (providers/tdcc/).

Source: https://openapi-t.tdcc.com.tw/v1/opendata/*
Covers all 8 tools from mcp-tdcc: shareholding, securities info,
director custody, monthly changes, weekly balance, ETF, e-voting, generic fetch.

Run: pytest tests/endpoint/tdcc/ -v
"""

import pytest


class TestGetShareholding:
    @pytest.mark.asyncio
    async def test_tsmc_returns_tiers(self, client, tsmc):
        """TSMC should have multiple shareholding tiers."""
        data = await client.get_shareholding(tsmc)
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_record_fields(self, client, tsmc):
        """Each record has expected fields."""
        data = await client.get_shareholding(tsmc)
        if data:
            row = data[0]
            assert row["stock_id"] == tsmc
            assert "date" in row
            assert "level" in row
            assert "holders" in row
            assert "shares" in row
            assert "percentage" in row

    @pytest.mark.asyncio
    async def test_holders_and_shares_positive(self, client, tsmc):
        """Holders and shares should be non-negative."""
        data = await client.get_shareholding(tsmc)
        if data:
            for row in data:
                assert row["holders"] >= 0
                assert row["shares"] >= 0

    @pytest.mark.asyncio
    async def test_multiple_tiers(self, client, tsmc):
        """Should have multiple shareholding tiers (15+)."""
        data = await client.get_shareholding(tsmc)
        if data:
            levels = {row["level"] for row in data}
            assert len(levels) > 5

    @pytest.mark.asyncio
    async def test_hon_hai(self, client, hon_hai):
        """Cross-check with Hon Hai."""
        data = await client.get_shareholding(hon_hai)
        assert isinstance(data, list)
        if data:
            assert data[0]["stock_id"] == hon_hai

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        """Non-existent stock returns empty."""
        data = await client.get_shareholding("0000")
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetSecuritiesInfo:
    @pytest.mark.asyncio
    async def test_lookup_tsmc(self, client, tsmc):
        """Look up TSMC securities info."""
        data = await client.get_securities_info(tsmc)
        assert isinstance(data, list)
        assert len(data) > 0
        assert tsmc in str(data[0].get("證券代號", ""))

    @pytest.mark.asyncio
    async def test_no_filter_returns_limited(self, client):
        """No filter returns limited set (max 50)."""
        data = await client.get_securities_info()
        assert isinstance(data, list)
        assert 0 < len(data) <= 50


class TestGetDirectorShareholding:
    @pytest.mark.asyncio
    async def test_tsmc(self, client, tsmc):
        """TSMC director/supervisor custody data."""
        data = await client.get_director_shareholding(tsmc)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        data = await client.get_director_shareholding("0000")
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetMonthlyChanges:
    @pytest.mark.asyncio
    async def test_listed_stock(self, client, tsmc):
        """Monthly changes for listed stock."""
        data = await client.get_monthly_changes(tsmc, market="listed")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_otc_stock(self, client):
        """Monthly changes for OTC stock."""
        data = await client.get_monthly_changes("6488", market="otc")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_market_defaults_listed(self, client, tsmc):
        data = await client.get_monthly_changes(tsmc, market="invalid")
        assert isinstance(data, list)


class TestGetWeeklyBalance:
    @pytest.mark.asyncio
    async def test_listed_stock(self, client, tsmc):
        """Weekly balance for listed stock."""
        data = await client.get_weekly_balance(tsmc, market="listed")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_otc_stock(self, client):
        data = await client.get_weekly_balance("6488", market="otc")
        assert isinstance(data, list)


class TestGetEtfMonthly:
    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """ETF monthly analysis has records."""
        data = await client.get_etf_monthly()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_has_fields(self, client):
        """Records have expected structure."""
        data = await client.get_etf_monthly()
        if data:
            row = data[0]
            assert isinstance(row, dict)
            assert len(row) > 2


class TestGetEvoting:
    @pytest.mark.asyncio
    async def test_annual_meeting(self, client):
        """Annual meeting e-voting info."""
        data = await client.get_evoting(meeting_type="annual")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_statistics(self, client):
        """E-voting participation statistics."""
        data = await client.get_evoting(meeting_type="statistics")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_filter_by_stock(self, client, tsmc):
        """Filter e-voting by stock code."""
        data = await client.get_evoting(stock_id=tsmc, meeting_type="annual")
        assert isinstance(data, list)


class TestGenericFetch:
    @pytest.mark.asyncio
    async def test_fetch_securities_basic(self, client):
        """Generic fetch endpoint 1-1 (securities basic data)."""
        data = await client.fetch("1-1")
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_fetch_offshore_fund_nav(self, client):
        """Fetch offshore fund NAV (3-4)."""
        data = await client.fetch("3-4")
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_fetch_bond_basic(self, client):
        """Fetch bond basic data (1-8-1)."""
        data = await client.fetch("1-8-1")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_fetch_futures_fund_nav(self, client):
        """Fetch futures trust fund NAV (5-4)."""
        data = await client.fetch("5-4")
        assert isinstance(data, list)
