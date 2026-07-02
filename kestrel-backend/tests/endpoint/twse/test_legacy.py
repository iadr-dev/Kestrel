"""Live tests for TWSE legacy Web API (exchangeReport + fund endpoints).

Covers: fetch_exchange_report, fetch_fund_report, get_stock_history,
        get_margin_balance, get_institutional_summary

Run: pytest tests/endpoint/twse/test_legacy.py -v
"""

import pytest


class TestFetchExchangeReport:
    """Test legacy exchangeReport bulk endpoints."""

    @pytest.mark.asyncio
    async def test_stock_day_all(self, client):
        """All stocks daily OHLCV (STOCK_DAY_ALL)."""
        raw = await client.fetch_exchange_report("STOCK_DAY_ALL", params={"response": "json"})
        assert raw is not None
        if isinstance(raw, dict):
            assert "data" in raw or "fields" in raw
        else:
            assert len(raw) > 100

    @pytest.mark.asyncio
    async def test_stock_day_avg_all(self, client):
        """Monthly average prices for all stocks."""
        raw = await client.fetch_exchange_report("STOCK_DAY_AVG_ALL", params={"response": "json"})
        assert raw is not None

    @pytest.mark.asyncio
    async def test_bwibbu_all(self, client):
        """P/E ratio, P/B ratio, dividend yield for all stocks."""
        raw = await client.fetch_exchange_report("BWIBBU_ALL", params={"response": "json"})
        assert raw is not None

    @pytest.mark.asyncio
    async def test_fmsrfk_all(self, client):
        """Market-wide institutional summary."""
        raw = await client.fetch_exchange_report("FMSRFK_ALL", params={"response": "json"})
        assert raw is not None


class TestGetStockHistory:
    """Test per-stock OHLCV history (STOCK_DAY)."""

    @pytest.mark.asyncio
    async def test_tsmc_current_month(self, client, tsmc):
        """TSMC OHLCV for current month."""
        from datetime import date
        today = date.today()
        data = await client.get_stock_history(tsmc, today.strftime("%Y%m01"))
        assert isinstance(data, list)
        assert len(data) > 0
        row = data[0]
        assert "date" in row
        assert row["date"].startswith(str(today.year))

    @pytest.mark.asyncio
    async def test_fields_present(self, client, tsmc):
        """Verify all expected fields in history record."""
        from datetime import date
        data = await client.get_stock_history(tsmc, date.today().strftime("%Y%m01"))
        if data:
            row = data[0]
            assert "日期" in row or "date" in row

    @pytest.mark.asyncio
    async def test_hon_hai(self, client, hon_hai):
        """Cross-check with Hon Hai."""
        from datetime import date
        data = await client.get_stock_history(hon_hai, date.today().strftime("%Y%m01"))
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        """Non-existent stock returns empty list."""
        data = await client.get_stock_history("0000", "20260101")
        assert data == []

    @pytest.mark.asyncio
    async def test_future_date_returns_empty(self, client, tsmc):
        """Future month returns empty."""
        data = await client.get_stock_history(tsmc, "20991201")
        assert data == []


class TestGetMarginBalance:
    """Test margin purchase / short sale balance."""

    @pytest.mark.asyncio
    async def test_single_stock(self, client, tsmc):
        """Margin balance for TSMC."""
        data = await client.get_margin_balance(tsmc)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_no_filter_returns_aggregate(self, client):
        """Margin balance without stock_no returns market-level aggregates."""
        data = await client.get_margin_balance()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_specific_date(self, client, tsmc):
        """Margin balance for a known past date."""
        data = await client.get_margin_balance(tsmc, "20260601")
        assert isinstance(data, list)


class TestGetInstitutionalSummary:
    """Test institutional investor buy/sell summary (T86)."""

    @pytest.mark.asyncio
    async def test_returns_sorted_list(self, client):
        """Returns top stocks by institutional net buy/sell."""
        data = await client.get_institutional_summary(limit=20)
        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.asyncio
    async def test_has_stock_identifiers(self, client):
        """Each record has stock code."""
        data = await client.get_institutional_summary(limit=5)
        if data:
            row = data[0]
            assert "證券代號" in row or "股票代號" in row

    @pytest.mark.asyncio
    async def test_sorted_by_net_buy(self, client):
        """Results sorted by absolute institutional net buy/sell."""
        data = await client.get_institutional_summary(limit=10)
        if len(data) >= 2:
            def get_abs_net(r):
                val = str(r.get("三大法人買賣超股數", "0")).replace(",", "")
                return abs(int(val or "0"))
            assert get_abs_net(data[0]) >= get_abs_net(data[1])

    @pytest.mark.asyncio
    async def test_custom_date(self, client):
        """Query specific date."""
        data = await client.get_institutional_summary(date="20260601", limit=5)
        assert isinstance(data, list)
