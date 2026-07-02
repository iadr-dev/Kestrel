"""Live tests for yfinance screener module.

Covers: search, search_news, lookup, screen, screen_custom, subscribe_realtime

Run: pytest tests/endpoint/yfinance/test_screener.py -v
"""

import pytest


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_by_name(self, yf):
        data = await yf.search("Tesla", max_results=5)
        assert len(data) > 0
        assert any("TSLA" in r.get("symbol", "") for r in data)

    @pytest.mark.asyncio
    async def test_search_by_symbol(self, yf):
        data = await yf.search("NVDA", max_results=5)
        assert len(data) > 0
        assert data[0]["symbol"] == "NVDA"

    @pytest.mark.asyncio
    async def test_search_returns_fields(self, yf):
        data = await yf.search("Apple", max_results=3)
        assert len(data) > 0
        result = data[0]
        assert "symbol" in result
        assert "name" in result
        assert "exchange" in result

    @pytest.mark.asyncio
    async def test_search_max_results_limit(self, yf):
        data = await yf.search("stock", max_results=3)
        assert len(data) <= 3

    @pytest.mark.asyncio
    async def test_search_no_results(self, yf):
        data = await yf.search("zzzzqqqq_no_match_ever_12345")
        assert isinstance(data, list)


class TestSearchNews:
    @pytest.mark.asyncio
    async def test_returns_news(self, yf):
        data = await yf.search_news("NVIDIA earnings")
        assert isinstance(data, list)
        if data:
            article = data[0]
            assert "title" in article
            assert "link" in article

    @pytest.mark.asyncio
    async def test_generic_query(self, yf):
        data = await yf.search_news("stock market")
        assert isinstance(data, list)


class TestLookup:
    @pytest.mark.asyncio
    async def test_lookup_stock(self, yf):
        data = await yf.lookup("Apple", asset_type="stock")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_lookup_etf(self, yf):
        data = await yf.lookup("S&P 500", asset_type="etf")
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_lookup_cryptocurrency(self, yf):
        data = await yf.lookup("Bitcoin", asset_type="cryptocurrency")
        assert isinstance(data, list)


class TestScreen:
    @pytest.mark.asyncio
    async def test_most_actives(self, yf):
        data = await yf.screen("most_actives", size=10)
        assert len(data) > 0
        assert len(data) <= 10
        row = data[0]
        assert "symbol" in row
        assert "price" in row
        assert "volume" in row

    @pytest.mark.asyncio
    async def test_day_gainers(self, yf):
        data = await yf.screen("day_gainers", size=5)
        assert len(data) > 0
        for row in data:
            assert row.get("change_pct") is None or row["change_pct"] >= 0

    @pytest.mark.asyncio
    async def test_day_losers(self, yf):
        data = await yf.screen("day_losers", size=5)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_size_parameter(self, yf):
        data = await yf.screen("most_actives", size=3)
        assert len(data) <= 3


class TestScreenCustom:
    @pytest.mark.asyncio
    async def test_equity_market_cap_filter(self, yf):
        data = await yf.screen_custom(
            query_type="equity",
            filters=[{"op": "gt", "field": "intradaymarketcap", "value": 100_000_000_000}],
            sort_field="intradaymarketcap",
            sort_asc=False,
            size=10,
        )
        assert len(data) > 0
        for row in data:
            assert row.get("market_cap") is None or row["market_cap"] > 0

    @pytest.mark.asyncio
    async def test_empty_filters_returns_empty(self, yf):
        data = await yf.screen_custom(
            query_type="equity",
            filters=[],
            size=5,
        )
        assert data == []

    @pytest.mark.asyncio
    async def test_multiple_filters(self, yf):
        data = await yf.screen_custom(
            query_type="equity",
            filters=[
                {"op": "gt", "field": "intradaymarketcap", "value": 50_000_000_000},
                {"op": "gt", "field": "regularmarketvolume.lasttwelvemonths", "value": 1_000_000},
            ],
            size=5,
        )
        assert isinstance(data, list)


class TestSubscribeRealtime:
    @pytest.mark.asyncio
    async def test_returns_price_data(self, yf):
        data = await yf.subscribe_realtime(["AAPL"])
        assert isinstance(data, dict)
        if data:
            key = list(data.keys())[0]
            snapshot = data[key]
            assert "price" in snapshot or "last_price" in snapshot
