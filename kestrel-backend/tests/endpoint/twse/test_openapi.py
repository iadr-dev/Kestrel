"""Live tests for TWSE OpenAPI endpoints (openapi.twse.com.tw/v1).

Covers: fetch_openapi (bulk list), fetch_company (single-stock lookup)
across company info, financials, market announcements, and metadata.

Run: pytest tests/endpoint/twse/test_openapi.py -v
"""

import pytest


class TestFetchOpenAPI:
    """Test bulk list endpoints that return all-stock data."""

    @pytest.mark.asyncio
    async def test_company_announcements(self, client):
        """Major company announcements (重大訊息)."""
        data = await client.fetch_openapi("/opendata/t187ap04_L")
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_notice_stocks(self, client):
        """注意股 (attention stocks)."""
        data = await client.fetch_openapi("/announcement/notice")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_disposal_stocks(self, client):
        """處置股 (disposal/punished stocks)."""
        data = await client.fetch_openapi("/announcement/punish")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_market_gain_loss_stats(self, client):
        """Market-wide gain/loss statistics."""
        data = await client.fetch_openapi("/opendata/twtazu_od")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_holiday_schedule(self, client):
        """Trading holiday schedule."""
        data = await client.fetch_openapi("/holidaySchedule/holidaySchedule")
        assert isinstance(data, list)
        assert len(data) > 0
        assert "Date" in data[0] or "Name" in data[0] or "日期" in data[0]

    @pytest.mark.asyncio
    async def test_broker_list(self, client):
        """Broker basic info list."""
        data = await client.fetch_openapi("/opendata/t187ap18")
        assert isinstance(data, list)
        assert len(data) > 50

    @pytest.mark.asyncio
    async def test_twse_news(self, client):
        """TWSE press releases."""
        data = await client.fetch_openapi("/news/newsList")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_stock_closing_quotes(self, client):
        """Daily closing quotes for all listed stocks."""
        data = await client.fetch_openapi("/exchangeReport/STOCK_DAY_ALL")
        assert isinstance(data, list)
        assert len(data) > 500

    @pytest.mark.asyncio
    async def test_monthly_revenue_all(self, client):
        """Monthly revenue for all listed stocks."""
        data = await client.fetch_openapi("/opendata/t187ap05_L")
        assert isinstance(data, list)
        assert len(data) > 100


class TestFetchCompany:
    """Test single-company lookup across various datasets."""

    @pytest.mark.asyncio
    async def test_company_profile(self, client, tsmc):
        """Company basic profile (公司基本資料)."""
        data = await client.fetch_company("/opendata/t187ap03_L", tsmc)
        assert data is not None
        assert data.get("公司代號") == tsmc or data.get("Code") == tsmc

    @pytest.mark.asyncio
    async def test_company_dividend(self, client, tsmc):
        """Dividend distribution history."""
        data = await client.fetch_company("/opendata/t187ap45_L", tsmc)
        assert data is not None
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_company_revenue(self, client, tsmc):
        """Monthly revenue for single stock."""
        data = await client.fetch_company("/opendata/t187ap05_L", tsmc)
        assert data is not None

    @pytest.mark.asyncio
    async def test_company_board_shareholdings(self, client, tsmc):
        """Board member shareholdings (董監持股)."""
        data = await client.fetch_company("/opendata/t187ap11_L", tsmc)
        assert data is not None

    @pytest.mark.asyncio
    async def test_company_income_statement(self, client, tsmc):
        """Income statement (一般工業)."""
        data = await client.fetch_company("/opendata/t187ap06_L_ci", tsmc)
        assert data is not None

    @pytest.mark.asyncio
    async def test_company_balance_sheet(self, client, tsmc):
        """Balance sheet."""
        data = await client.fetch_company("/opendata/t187ap07_L_ci", tsmc)
        assert data is not None

    @pytest.mark.asyncio
    async def test_company_profitability(self, client, tsmc):
        """Profitability analysis (獲利能力)."""
        data = await client.fetch_company("/opendata/t187ap17_L", tsmc)
        assert data is not None

    @pytest.mark.asyncio
    async def test_company_major_shareholders(self, client, tsmc):
        """Major shareholders (大股東持股)."""
        data = await client.fetch_company("/opendata/t187ap02_L", tsmc)
        assert data is None or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_company_esg_governance(self, client, tsmc):
        """ESG governance data — may not exist for all companies."""
        data = await client.fetch_company("/opendata/t187ap46_L_9", tsmc)
        assert data is None or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_nonexistent_stock_returns_none(self, client):
        """Lookup for invalid stock code returns None."""
        data = await client.fetch_company("/opendata/t187ap03_L", "9999")
        assert data is None

    @pytest.mark.asyncio
    async def test_hon_hai_profile(self, client, hon_hai):
        """Cross-check with second stock (Hon Hai)."""
        data = await client.fetch_company("/opendata/t187ap03_L", hon_hai)
        assert data is not None
        assert data.get("公司代號") == hon_hai or data.get("Code") == hon_hai
