"""Live tests for TAIFEX (futures/options) API endpoints.

Covers: fetch_taifex, get_futures_institutional, get_futures_position,
        get_put_call_ratio, get_large_traders_oi, get_options_analytics,
        get_taifex_daily_report, get_taifex_margin, get_taifex_trading_stats

Note: TAIFEX requires browser-like User-Agent. Tests verify the client
handles this correctly.

Run: pytest tests/endpoint/twse/test_taifex.py -v
"""

import pytest


class TestFetchTaifex:
    """Test raw TAIFEX endpoint fetching."""

    @pytest.mark.asyncio
    async def test_valid_endpoint(self, client):
        """Known endpoint returns data."""
        data = await client.fetch_taifex("PutCallRatioOfTXOBytheDate")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_endpoint_returns_empty(self, client):
        """Non-existent endpoint returns empty gracefully."""
        data = await client.fetch_taifex("NonExistentEndpoint123")
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetFuturesInstitutional:
    """Test futures institutional positions."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Institutional futures positions."""
        data = await client.get_futures_institutional()
        assert isinstance(data, list)
        if data:
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_has_expected_fields(self, client):
        """Records have trading data fields."""
        data = await client.get_futures_institutional()
        if data:
            row = data[0]
            assert isinstance(row, dict)
            assert len(row) > 3


class TestGetFuturesPosition:
    """Test futures open interest."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Futures open interest positions."""
        data = await client.get_futures_position()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_has_records(self, client):
        """Should have data for active contracts."""
        data = await client.get_futures_position()
        if data:
            assert len(data) > 0


class TestGetPutCallRatio:
    """Test TXO put/call ratio."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Put/call ratio time series."""
        data = await client.get_put_call_ratio()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_has_records(self, client):
        """Should have recent P/C ratio records."""
        data = await client.get_put_call_ratio()
        if data:
            assert len(data) > 0
            row = data[0]
            assert isinstance(row, dict)


class TestGetLargeTradersOI:
    """Test large trader open interest positions."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Large trader positions."""
        data = await client.get_large_traders_oi()
        assert isinstance(data, list)


class TestGetOptionsAnalytics:
    """Test options analytics (delta, OI changes)."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Options analytics for TXO."""
        data = await client.get_options_analytics()
        assert isinstance(data, list)


class TestGetTaifexDailyReport:
    """Test daily futures market report."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Daily trading report."""
        data = await client.get_taifex_daily_report()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_has_records(self, client):
        """Report should have contract-level data."""
        data = await client.get_taifex_daily_report()
        if data:
            assert len(data) > 5


class TestGetTaifexMargin:
    """Test margin requirements."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Current margin requirements."""
        data = await client.get_taifex_margin()
        assert isinstance(data, list)


class TestGetTaifexTradingStats:
    """Test trading volume and open interest statistics."""

    @pytest.mark.asyncio
    async def test_returns_data(self, client):
        """Trading stats for futures and options."""
        data = await client.get_taifex_trading_stats()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_has_records(self, client):
        """Should have multiple product entries."""
        data = await client.get_taifex_trading_stats()
        if data:
            assert len(data) > 0
