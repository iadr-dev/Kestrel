"""Live tests for FinMind macro/economic datasets.

Covers: TaiwanExchangeRate, GoldPrice, CrudeOilPrices,
        TaiwanBusinessIndicator

Run: pytest tests/endpoint/finmind/test_macro.py -v
"""

import pytest

from app.core.constants import FinMindDataset


class TestTaiwanExchangeRate:
    @pytest.mark.asyncio
    async def test_usd_rate(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_EXCHANGE_RATE,
            data_id="USD",
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert "date" in row

    @pytest.mark.asyncio
    async def test_jpy_rate(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_EXCHANGE_RATE,
            data_id="JPY",
            start_date=recent_start,
        )
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_eur_rate(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_EXCHANGE_RATE,
            data_id="EUR",
            start_date=recent_start,
        )
        assert len(data) > 0


class TestGoldPrice:
    @pytest.mark.asyncio
    async def test_returns_gold_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.GOLD_PRICE,
            start_date=recent_start,
        )
        assert isinstance(data, list)
        if data:
            assert "date" in data[0]


class TestCrudeOilPrices:
    @pytest.mark.asyncio
    async def test_returns_oil_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.CRUDE_OIL_PRICES,
            start_date=recent_start,
        )
        assert isinstance(data, list)
        if data:
            assert "date" in data[0]


class TestTaiwanBusinessIndicator:
    @pytest.mark.asyncio
    async def test_returns_indicators(self, provider, quarter_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_BUSINESS_INDICATOR,
            start_date=quarter_start,
        )
        assert isinstance(data, list)
