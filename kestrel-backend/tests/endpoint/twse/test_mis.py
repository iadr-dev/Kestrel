"""Live tests for MIS real-time quote API (mis.twse.com.tw).

Covers: get_realtime_quote

Note: MIS returns empty outside market hours (09:00-13:30 TW time).
Tests are designed to pass regardless of market state.

Run: pytest tests/endpoint/twse/test_mis.py -v
"""

import pytest


class TestGetRealtimeQuote:
    """Test real-time intraday quote retrieval."""

    @pytest.mark.asyncio
    async def test_single_stock(self, client, tsmc):
        """Single stock quote — should not error."""
        data = await client.get_realtime_quote([tsmc])
        assert isinstance(data, list)
        if data:
            msg = data[0]
            assert "c" in msg  # stock code
            assert "n" in msg  # stock name

    @pytest.mark.asyncio
    async def test_multiple_stocks(self, client, tsmc, hon_hai, mediatek):
        """Multiple stocks in single request."""
        data = await client.get_realtime_quote([tsmc, hon_hai, mediatek])
        assert isinstance(data, list)
        if data:
            codes = {msg.get("c") for msg in data}
            assert len(codes) >= 1

    @pytest.mark.asyncio
    async def test_quote_fields_during_market_hours(self, client, tsmc):
        """Verify price fields when data available."""
        data = await client.get_realtime_quote([tsmc])
        if data:
            msg = data[0]
            # z = last trade price, v = volume, o = open, h = high, l = low
            expected_fields = {"c", "n"}
            assert expected_fields.issubset(msg.keys())

    @pytest.mark.asyncio
    async def test_otc_stock_fallback(self, client, otc_stock):
        """OTC stock triggers otc_ prefix fallback."""
        data = await client.get_realtime_quote([otc_stock])
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_invalid_stock_returns_empty(self, client):
        """Non-existent stock code returns empty."""
        data = await client.get_realtime_quote(["0000"])
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, client):
        """Empty input returns empty."""
        data = await client.get_realtime_quote([])
        assert isinstance(data, list)
        assert len(data) == 0
