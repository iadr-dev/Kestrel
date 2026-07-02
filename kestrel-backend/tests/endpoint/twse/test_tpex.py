"""Live tests for TPEx (OTC market) API endpoints.

Covers: fetch_tpex, get_otc_daily, get_otc_institutional, get_otc_pe_ratio

Note: TPEx may rate-limit or block automated requests.
Tests are resilient to empty responses from anti-scraping measures.

Run: pytest tests/endpoint/twse/test_tpex.py -v
"""

import pytest


class TestFetchTpex:
    """Test raw TPEx OpenAPI endpoint fetching."""

    @pytest.mark.asyncio
    async def test_daily_close_quotes(self, client):
        """Mainboard daily close quotes."""
        data = await client.fetch_tpex("tpex_mainboard_daily_close_quotes")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_institutional_buy_sell(self, client):
        """Institutional investors buy/sell."""
        data = await client.fetch_tpex("tpex_institutional_investors_buy_sell")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_pe_ratio(self, client):
        """P/E ratio."""
        data = await client.fetch_tpex("tpex_peratio")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_endpoint_returns_empty(self, client):
        """Non-existent endpoint returns empty gracefully."""
        data = await client.fetch_tpex("nonexistent_endpoint_xyz")
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetOTCDaily:
    """Test OTC daily price data."""

    @pytest.mark.asyncio
    async def test_all_stocks(self, client):
        """All OTC stocks daily prices."""
        data = await client.get_otc_daily(limit=20)
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.asyncio
    async def test_single_stock(self, client, otc_stock):
        """Specific OTC stock daily price."""
        data = await client.get_otc_daily(otc_stock, limit=5)
        assert isinstance(data, list)
        if data:
            assert all(d.get("SecuritiesCompanyCode") == otc_stock for d in data)

    @pytest.mark.asyncio
    async def test_nonexistent_stock_returns_empty(self, client):
        """Invalid stock code returns empty."""
        data = await client.get_otc_daily("0000", limit=5)
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetOTCInstitutional:
    """Test OTC institutional buy/sell."""

    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        """Returns institutional trading data."""
        data = await client.get_otc_institutional()
        assert isinstance(data, list)


class TestGetOTCPERatio:
    """Test OTC P/E ratio data."""

    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        """Returns P/E data for OTC stocks."""
        data = await client.get_otc_pe_ratio()
        assert isinstance(data, list)
