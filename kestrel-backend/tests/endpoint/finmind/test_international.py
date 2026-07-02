"""Live tests for FinMind international stock datasets.

Covers: USStockPrice, USStockInfo, UKStockPrice, EuropeStockPrice, JapanStockPrice

Run: pytest tests/endpoint/finmind/test_international.py -v
"""

import pytest

from app.core.constants import FinMindDataset


class TestUSStockPrice:
    @pytest.mark.asyncio
    async def test_returns_us_ohlcv(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.US_STOCK_PRICE,
            data_id="AAPL",
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == "AAPL"
        assert "close" in row or "Close" in row

    @pytest.mark.asyncio
    async def test_nvidia(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.US_STOCK_PRICE,
            data_id="NVDA",
            start_date=recent_start,
        )
        assert len(data) > 0
        assert data[0]["stock_id"] == "NVDA"


class TestUSStockInfo:
    @pytest.mark.asyncio
    async def test_returns_stock_list(self, provider):
        data = await provider.fetch_dataset(FinMindDataset.US_STOCK_INFO)
        assert len(data) > 100
        aapl = [s for s in data if s.get("stock_id") == "AAPL"]
        assert len(aapl) >= 1


class TestUKStockPrice:
    @pytest.mark.asyncio
    async def test_returns_uk_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.UK_STOCK_PRICE,
            data_id="VOD",
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestEuropeStockPrice:
    @pytest.mark.asyncio
    async def test_returns_europe_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.EUROPE_STOCK_PRICE,
            data_id="SAP",
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestJapanStockPrice:
    @pytest.mark.asyncio
    async def test_returns_japan_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.JAPAN_STOCK_PRICE,
            data_id="7203",
            start_date=recent_start,
        )
        assert isinstance(data, list)
