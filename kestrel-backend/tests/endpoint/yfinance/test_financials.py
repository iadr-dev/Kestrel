"""Live tests for yfinance financials module.

Covers: get_financials, get_quarterly_financials, get_ttm_financials,
        get_earnings, get_earnings_dates, get_sec_filings

Run: pytest tests/endpoint/yfinance/test_financials.py -v
"""

import pytest


class TestGetFinancials:
    @pytest.mark.asyncio
    async def test_annual_statements(self, yf, us_ticker):
        data = await yf.get_financials(us_ticker)
        assert data["ticker"] == us_ticker
        assert "income_statement" in data
        assert "columns" in data["income_statement"]
        assert len(data["income_statement"]["columns"]) > 0
        assert "balance_sheet" in data
        assert "cash_flow" in data

    @pytest.mark.asyncio
    async def test_tw_stock(self, yf, tw_ticker):
        data = await yf.get_financials(tw_ticker)
        assert data["ticker"] == tw_ticker
        assert "income_statement" in data


class TestGetQuarterlyFinancials:
    @pytest.mark.asyncio
    async def test_quarterly_statements(self, yf, us_ticker):
        data = await yf.get_quarterly_financials(us_ticker)
        assert data["ticker"] == us_ticker
        assert "quarterly_income" in data
        assert "columns" in data["quarterly_income"]
        assert len(data["quarterly_income"]["columns"]) >= 4

    @pytest.mark.asyncio
    async def test_has_balance_sheet_and_cashflow(self, yf, us_ticker):
        data = await yf.get_quarterly_financials(us_ticker)
        assert "quarterly_balance_sheet" in data
        assert "quarterly_cashflow" in data


class TestGetTTMFinancials:
    @pytest.mark.asyncio
    async def test_ttm_data(self, yf, us_ticker):
        data = await yf.get_ttm_financials(us_ticker)
        assert data["ticker"] == us_ticker
        has_data = "ttm_income_stmt" in data or "ttm_cashflow" in data
        assert has_data or "error" not in data


class TestGetEarnings:
    @pytest.mark.asyncio
    async def test_returns_earnings_dict(self, yf, us_ticker):
        """Deprecated in yfinance 1.4+ — may return empty dict."""
        data = await yf.get_earnings(us_ticker)
        assert data["ticker"] == us_ticker
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_annual_has_records_if_available(self, yf, us_ticker):
        data = await yf.get_earnings(us_ticker)
        if "annual" in data:
            assert len(data["annual"]) > 0


class TestGetEarningsDates:
    @pytest.mark.asyncio
    async def test_returns_dates_or_error(self, yf, us_ticker):
        """Requires lxml — may return error if not installed."""
        data = await yf.get_earnings_dates(us_ticker)
        assert data["ticker"] == us_ticker
        assert "earnings_dates" in data or "error" in data


class TestGetSecFilings:
    @pytest.mark.asyncio
    async def test_returns_filing_list(self, yf, us_ticker):
        data = await yf.get_sec_filings(us_ticker)
        assert isinstance(data, list)
        assert len(data) > 0
        filing = data[0]
        assert "type" in filing or "exhibits" in filing

    @pytest.mark.asyncio
    async def test_tw_stock_may_be_empty(self, yf, tw_ticker):
        data = await yf.get_sec_filings(tw_ticker)
        assert isinstance(data, list)
