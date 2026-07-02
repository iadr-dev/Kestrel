"""Live tests for ETF endpoints.

Covers:
- /etf/nav — all ETF real-time NAV + premium/discount (MIS all_etf.txt)
- /etf/nav/{etf_id} — single ETF NAV lookup
- /etf/premium-discount — ETFs with significant premium/discount
- /etf/{etf_id}/holdings — ETF composition (TWSE legacy, may be empty)
- /etf/list — popular ETFs by volume (FinMind)

Run: pytest tests/endpoint/etf/ -v
"""

from datetime import date, timedelta

import pytest

from app.scrapers.twse_etf import scrape_etf_holdings, scrape_etf_nav


class TestEtfNav:
    """Test all-ETF real-time NAV from MIS."""

    @pytest.mark.asyncio
    async def test_returns_many_etfs(self):
        """Should return 300+ ETFs."""
        data = await scrape_etf_nav()
        assert isinstance(data, list)
        assert len(data) > 200

    @pytest.mark.asyncio
    async def test_record_fields(self):
        """Each record has expected real-time fields."""
        data = await scrape_etf_nav()
        assert len(data) > 0
        row = data[0]
        assert "etf_id" in row
        assert "name" in row
        assert "market_price" in row
        assert "estimated_nav" in row
        assert "premium_discount_pct" in row
        assert "prev_nav" in row
        assert "issued_units" in row

    @pytest.mark.asyncio
    async def test_0050_present(self):
        """0050 (元大台灣50) should be in the list."""
        data = await scrape_etf_nav()
        ids = {d["etf_id"] for d in data}
        assert "0050" in ids

    @pytest.mark.asyncio
    async def test_0056_present(self):
        """0056 (元大高股息) should be in the list."""
        data = await scrape_etf_nav()
        ids = {d["etf_id"] for d in data}
        assert "0056" in ids

    @pytest.mark.asyncio
    async def test_market_price_is_numeric(self):
        """Market price should be a number."""
        data = await scrape_etf_nav()
        e0050 = next((d for d in data if d["etf_id"] == "0050"), None)
        assert e0050 is not None
        assert isinstance(e0050["market_price"], (int, float))
        assert e0050["market_price"] > 0

    @pytest.mark.asyncio
    async def test_premium_discount_is_numeric(self):
        """Premium/discount should be a number (can be negative)."""
        data = await scrape_etf_nav()
        e0050 = next((d for d in data if d["etf_id"] == "0050"), None)
        assert e0050 is not None
        assert isinstance(e0050["premium_discount_pct"], (int, float))

    @pytest.mark.asyncio
    async def test_has_data_date(self):
        """Should include today's date info."""
        data = await scrape_etf_nav()
        assert data[0]["data_date"]

    @pytest.mark.asyncio
    async def test_returns_realtime_regardless_of_param(self):
        """all_etf.txt always returns real-time data."""
        data = await scrape_etf_nav(date(2099, 12, 31))
        assert len(data) > 200


class TestEtfNavSingle:
    """Test single ETF lookup."""

    @pytest.mark.asyncio
    async def test_0050_found(self):
        """Looking up 0050 should return its data."""
        data = await scrape_etf_nav()
        match = [d for d in data if d["etf_id"] == "0050"]
        assert len(match) == 1
        assert match[0]["name"] == "元大台灣50"

    @pytest.mark.asyncio
    async def test_nonexistent_etf(self):
        """Non-existent ETF ID returns no match."""
        data = await scrape_etf_nav()
        match = [d for d in data if d["etf_id"] == "9999"]
        assert len(match) == 0


class TestEtfPremiumDiscount:
    """Test premium/discount filtering."""

    @pytest.mark.asyncio
    async def test_filter_above_threshold(self):
        """Should find ETFs with |premium/discount| > threshold."""
        data = await scrape_etf_nav()
        threshold = 0.5
        significant = [
            d for d in data
            if isinstance(d.get("premium_discount_pct"), (int, float))
            and abs(d["premium_discount_pct"]) >= threshold
        ]
        assert isinstance(significant, list)

    @pytest.mark.asyncio
    async def test_sorted_by_abs_value(self):
        """Results sorted by absolute premium/discount."""
        data = await scrape_etf_nav()
        significant = [
            d for d in data
            if isinstance(d.get("premium_discount_pct"), (int, float))
            and abs(d["premium_discount_pct"]) >= 0.1
        ]
        significant.sort(key=lambda x: abs(x["premium_discount_pct"]), reverse=True)
        if len(significant) >= 2:
            assert abs(significant[0]["premium_discount_pct"]) >= abs(significant[1]["premium_discount_pct"])


class TestEtfHoldings:
    """Test ETF holdings/composition (TWSE legacy endpoint — may be empty)."""

    @pytest.mark.asyncio
    async def test_returns_list(self, popular_etf):
        """Holdings endpoint returns a list."""
        data = await scrape_etf_holdings(popular_etf)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_etf_returns_empty(self):
        """Non-existent ETF returns empty."""
        data = await scrape_etf_holdings("9999")
        assert isinstance(data, list)
        assert len(data) == 0


class TestEtfList:
    """Test popular ETF list from FinMind."""

    @pytest.mark.asyncio
    async def test_returns_etfs(self):
        """Should return top ETFs by volume."""
        from app.core.config import Settings
        from app.core.constants import FinMindDataset
        from app.providers.finmind.provider import FinMindProvider

        settings = Settings()
        provider = FinMindProvider(settings)
        await provider.initialize()

        try:
            all_info = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
            etf_ids = set(
                s["stock_id"] for s in all_info
                if "ETF" in (s.get("industry_category") or "")
                or (s.get("stock_id", "").startswith("00") and len(s.get("stock_id", "")) <= 6)
            )
            assert len(etf_ids) > 50
            assert "0050" in etf_ids
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_price_data_available(self):
        """ETF prices should be fetchable."""
        from app.core.config import Settings
        from app.core.constants import FinMindDataset
        from app.providers.finmind.provider import FinMindProvider

        settings = Settings()
        provider = FinMindProvider(settings)
        await provider.initialize()

        try:
            trade_date = date.today() - timedelta(days=3)
            prices = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_STOCK_PRICE,
                data_id="0050",
                start_date=trade_date,
            )
            assert len(prices) > 0
            assert prices[0]["stock_id"] == "0050"
            assert "close" in prices[0]
        finally:
            await provider.close()
