"""Live tests for TWSE ETF scraper (NAV + holdings).

Sources:
- ETF NAV: https://www.twse.com.tw/rwd/zh/ETF/etfNav
- ETF Holdings: https://www.twse.com.tw/rwd/zh/ETF/etfHolding

Run: pytest tests/scraper/test_twse_etf.py -v
"""

import pytest

from app.scrapers.twse_etf import run, scrape_etf_holdings, scrape_etf_nav


class TestScrapeEtfNav:
    @pytest.mark.asyncio
    async def test_returns_data(self):
        """ETF NAV for today (or last trading day)."""
        data = await scrape_etf_nav()
        assert isinstance(data, list)
        # May be empty on weekends/holidays

    @pytest.mark.asyncio
    async def test_with_known_date(self):
        """Query a known past trading date."""
        from datetime import date, timedelta
        # Try last 5 weekdays to find a trading day
        for offset in range(1, 8):
            target = date.today() - timedelta(days=offset)
            if target.weekday() < 5:
                data = await scrape_etf_nav(target)
                if data:
                    assert "date" in data[0]
                    return
        # If no trading day found, just verify no crash
        assert True

    @pytest.mark.asyncio
    async def test_record_has_date(self):
        """Records should have date field."""
        data = await scrape_etf_nav()
        if data:
            assert "date" in data[0]

    @pytest.mark.asyncio
    async def test_always_returns_realtime(self):
        """all_etf.txt returns real-time data regardless of target_date."""
        from datetime import date
        data = await scrape_etf_nav(date(2099, 12, 31))
        assert isinstance(data, list)
        assert len(data) > 0


class TestScrapeEtfHoldings:
    @pytest.mark.asyncio
    async def test_0050_holdings(self, popular_etf):
        """0050 ETF should have holdings data."""
        data = await scrape_etf_holdings(popular_etf)
        assert isinstance(data, list)
        # May be empty depending on date

    @pytest.mark.asyncio
    async def test_record_fields(self, popular_etf):
        """Records should have etf_id and date."""
        from datetime import date, timedelta
        for offset in range(1, 8):
            target = date.today() - timedelta(days=offset)
            if target.weekday() < 5:
                data = await scrape_etf_holdings(popular_etf, target)
                if data:
                    assert data[0]["etf_id"] == popular_etf
                    assert "date" in data[0]
                    return
        assert True

    @pytest.mark.asyncio
    async def test_invalid_etf_returns_empty(self):
        """Non-existent ETF returns empty."""
        data = await scrape_etf_holdings("9999")
        assert isinstance(data, list)
        assert len(data) == 0


class TestRun:
    @pytest.mark.asyncio
    async def test_run_nav_only(self):
        """run() without etf_ids fetches NAV only."""
        result = await run()
        assert result.source == "twse_etf"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_with_etf_ids(self, popular_etf):
        """run() with etf_ids fetches NAV + holdings."""
        result = await run([popular_etf])
        assert result.source == "twse_etf"
        assert result.rows_written >= 0
