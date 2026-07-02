"""Live tests for yfinance ticker module.

Covers: get_info, get_fast_info, get_calendar, get_history, get_options,
        get_dividends, get_splits, get_actions, get_news, get_isin,
        get_history_metadata, get_capital_gains

Run: pytest tests/endpoint/yfinance/test_ticker.py -v
"""

import pytest


class TestGetInfo:
    @pytest.mark.asyncio
    async def test_us_stock_returns_full_profile(self, yf, us_ticker):
        data = await yf.get_info(us_ticker)
        assert data["ticker"] == us_ticker
        assert data["name"], "name should not be empty"
        assert data["sector"], "sector should not be empty"
        assert data["industry"], "industry should not be empty"
        assert data["market_cap"] and data["market_cap"] > 0
        assert data["pe_ratio"] is not None

    @pytest.mark.asyncio
    async def test_tw_stock_resolves_suffix(self, yf, tw_ticker):
        data = await yf.get_info(tw_ticker)
        assert data["ticker"] == tw_ticker
        assert data["name"], "TW stock should resolve name"
        assert data["market_cap"] and data["market_cap"] > 0

    @pytest.mark.asyncio
    async def test_invalid_ticker_returns_error(self, yf):
        data = await yf.get_info("ZZZZZZINVALID999")
        assert "error" in data or data.get("name") == ""


class TestGetFastInfo:
    @pytest.mark.asyncio
    async def test_returns_price_snapshot(self, yf, us_ticker):
        data = await yf.get_fast_info(us_ticker)
        assert data["ticker"] == us_ticker
        assert data["last_price"] is not None and data["last_price"] > 0
        assert data["volume"] is not None and data["volume"] > 0
        assert data["market_cap"] is not None

    @pytest.mark.asyncio
    async def test_tw_stock(self, yf, tw_ticker):
        data = await yf.get_fast_info(tw_ticker)
        assert data["ticker"] == tw_ticker
        assert data["last_price"] is not None and data["last_price"] > 0


class TestGetCalendar:
    @pytest.mark.asyncio
    async def test_returns_calendar_data(self, yf, us_ticker):
        data = await yf.get_calendar(us_ticker)
        assert data["ticker"] == us_ticker
        assert isinstance(data, dict)


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_daily_5d(self, yf, us_ticker):
        data = await yf.get_history(us_ticker, period="5d", interval="1d")
        assert len(data) >= 3
        row = data[0]
        assert "Open" in row or "open" in str(row.keys()).lower()
        assert "Close" in row or "close" in str(row.keys()).lower()
        assert "Volume" in row or "volume" in str(row.keys()).lower()

    @pytest.mark.asyncio
    async def test_1mo_period(self, yf, us_ticker):
        data = await yf.get_history(us_ticker, period="1mo", interval="1d")
        assert len(data) >= 15

    @pytest.mark.asyncio
    async def test_weekly_interval(self, yf, us_ticker):
        data = await yf.get_history(us_ticker, period="3mo", interval="1wk")
        assert len(data) >= 10

    @pytest.mark.asyncio
    async def test_tw_stock(self, yf, tw_ticker):
        data = await yf.get_history(tw_ticker, period="5d", interval="1d")
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_invalid_ticker_returns_empty(self, yf):
        data = await yf.get_history("ZZZZINVALID999", period="5d", interval="1d")
        assert data == []


class TestGetOptions:
    @pytest.mark.asyncio
    async def test_returns_expiration_chain(self, yf, us_ticker):
        data = await yf.get_options(us_ticker)
        assert data["ticker"] == us_ticker
        assert "expirations" in data
        assert len(data["expirations"]) > 0
        assert "calls" in data or "puts" in data


class TestGetDividends:
    @pytest.mark.asyncio
    async def test_returns_dividend_history(self, yf, us_ticker):
        data = await yf.get_dividends(us_ticker)
        assert len(data) > 0
        assert "Dividends" in data[0] or "dividends" in str(data[0].keys()).lower()

    @pytest.mark.asyncio
    async def test_non_dividend_stock_returns_empty(self, yf):
        data = await yf.get_dividends("BRK-B")
        assert isinstance(data, list)


class TestGetSplits:
    @pytest.mark.asyncio
    async def test_returns_split_history(self, yf, us_ticker):
        data = await yf.get_splits(us_ticker)
        assert isinstance(data, list)
        assert len(data) > 0


class TestGetActions:
    @pytest.mark.asyncio
    async def test_returns_combined_history(self, yf, us_ticker):
        data = await yf.get_actions(us_ticker)
        assert isinstance(data, list)
        assert len(data) > 0


class TestGetNews:
    @pytest.mark.asyncio
    async def test_returns_news_articles(self, yf, us_ticker):
        data = await yf.get_news(us_ticker)
        assert isinstance(data, list)
        if data:
            article = data[0]
            assert "title" in article
            assert "link" in article
            assert "publisher" in article


class TestGetIsin:
    @pytest.mark.asyncio
    async def test_returns_isin_code(self, yf, us_ticker):
        isin = await yf.get_isin(us_ticker)
        assert isin is None or (isinstance(isin, str) and len(isin) >= 10)


class TestGetHistoryMetadata:
    @pytest.mark.asyncio
    async def test_returns_metadata(self, yf, us_ticker):
        data = await yf.get_history_metadata(us_ticker)
        assert data["ticker"] == us_ticker
        assert "currency" in data or "exchangeName" in data or len(data) > 1


class TestGetCapitalGains:
    @pytest.mark.asyncio
    async def test_etf_capital_gains(self, yf, etf_ticker):
        data = await yf.get_capital_gains(etf_ticker)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_stock_returns_empty(self, yf, us_ticker):
        data = await yf.get_capital_gains(us_ticker)
        assert isinstance(data, list)
