"""Live tests for MOPS provider (providers/mops/).

Source: https://mops.twse.com.tw
Covers: company profile, material announcements, treasury stock,
        investor conferences, director holdings.

Note: MOPS may block automated requests from non-browser environments.
Tests are resilient to empty/error responses.

Run: pytest tests/endpoint/mops/ -v
"""

from datetime import date

import pytest


class TestGetCompanyProfile:
    @pytest.mark.asyncio
    async def test_tsmc_returns_dict(self, client, tsmc):
        """Should return a dict with stock_id."""
        data = await client.get_company_profile(tsmc)
        assert data["stock_id"] == tsmc
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_has_market_field(self, client, tsmc):
        """Should include market=TW when MOPS responds."""
        data = await client.get_company_profile(tsmc)
        if "error" not in data:
            assert data.get("market") == "TW"

    @pytest.mark.asyncio
    async def test_profile_fields_if_available(self, client, tsmc):
        """If MOPS responds, should have company name/chairman."""
        data = await client.get_company_profile(tsmc)
        if "error" not in data:
            assert data.get("name_zh") or data.get("chairman")

    @pytest.mark.asyncio
    async def test_hon_hai(self, client, hon_hai):
        """Cross-check with Hon Hai."""
        data = await client.get_company_profile(hon_hai)
        assert data["stock_id"] == hon_hai

    @pytest.mark.asyncio
    async def test_invalid_stock(self, client):
        """Non-existent stock returns error or empty profile."""
        data = await client.get_company_profile("0000")
        assert data["stock_id"] == "0000"


class TestGetAnnouncements:
    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        """Announcements endpoint returns a list."""
        data = await client.get_announcements()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_by_stock_id(self, client, tsmc):
        """Filter by stock_id."""
        data = await client.get_announcements(stock_id=tsmc)
        assert isinstance(data, list)
        if data:
            assert any(tsmc in r.get("stock_id", "") for r in data)

    @pytest.mark.asyncio
    async def test_by_keyword(self, client):
        """Filter by keyword."""
        data = await client.get_announcements(keyword="董事")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_record_fields(self, client):
        """Records have expected fields if data returned."""
        data = await client.get_announcements()
        if data:
            row = data[0]
            assert "stock_id" in row
            assert "subject" in row


class TestGetTreasuryStock:
    @pytest.mark.asyncio
    async def test_returns_list(self, client, tsmc):
        """Treasury stock returns a list."""
        data = await client.get_treasury_stock(tsmc)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_record_fields(self, client, tsmc):
        """Records have expected fields if data exists."""
        data = await client.get_treasury_stock(tsmc)
        if data:
            row = data[0]
            assert row["stock_id"] == tsmc
            assert "purpose" in row
            assert "planned_shares" in row

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        data = await client.get_treasury_stock("0000")
        assert isinstance(data, list)


class TestGetInvestorConferences:
    @pytest.mark.asyncio
    async def test_returns_list(self, client):
        """Investor conferences returns a list."""
        data = await client.get_investor_conferences()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_by_stock(self, client, tsmc):
        """Filter by stock_id."""
        data = await client.get_investor_conferences(stock_id=tsmc)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_record_fields(self, client):
        """Records have expected fields if data exists."""
        data = await client.get_investor_conferences()
        if data:
            row = data[0]
            assert "company_name" in row or "stock_id" in row
            assert "date" in row


class TestGetDirectorHoldings:
    @pytest.mark.asyncio
    async def test_returns_list(self, client, tsmc):
        """Director holdings returns a list."""
        data = await client.get_director_holdings(tsmc)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_record_fields(self, client, tsmc):
        """Records have expected fields if data exists."""
        data = await client.get_director_holdings(tsmc)
        if data:
            row = data[0]
            assert row["stock_id"] == tsmc
            assert "name" in row
            assert "title" in row

    @pytest.mark.asyncio
    async def test_with_specific_date(self, client, tsmc):
        """Query with explicit date."""
        data = await client.get_director_holdings(tsmc, date(2026, 5, 1))
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        data = await client.get_director_holdings("0000")
        assert isinstance(data, list)
