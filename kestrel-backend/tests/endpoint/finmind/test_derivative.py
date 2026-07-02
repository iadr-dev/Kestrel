"""Live tests for FinMind derivative (futures/options) datasets.

Covers: TaiwanFuturesDaily, TaiwanOptionDaily, TaiwanFuturesInstitutional,
        TaiwanOptionInstitutional, TaiwanFuturesLargeTraders,
        TaiwanOptionLargeTraders

Run: pytest tests/endpoint/finmind/test_derivative.py -v
"""

import pytest

from app.core.constants import FinMindDataset


class TestTaiwanFuturesDaily:
    @pytest.mark.asyncio
    async def test_returns_futures_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_FUTURES_DAILY,
            data_id="TX",
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert "date" in row
        assert "open" in row or "Open" in row

    @pytest.mark.asyncio
    async def test_mini_futures(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_FUTURES_DAILY,
            data_id="MTX",
            start_date=recent_start,
        )
        assert len(data) > 0


class TestTaiwanOptionDaily:
    @pytest.mark.asyncio
    async def test_returns_option_data(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_OPTION_DAILY,
            data_id="TXO",
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert "date" in row


class TestTaiwanFuturesInstitutional:
    @pytest.mark.asyncio
    async def test_institutional_positions(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL,
            data_id="TX",
            start_date=recent_start,
        )
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_multiple_investor_types(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL,
            data_id="TX",
            start_date=recent_start,
        )
        names = {row.get("institutional_investors") or row.get("name") for row in data}
        assert len(names) > 1


class TestTaiwanOptionInstitutional:
    @pytest.mark.asyncio
    async def test_option_institutional(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_OPTION_INSTITUTIONAL,
            data_id="TXO",
            start_date=recent_start,
        )
        assert len(data) > 0


class TestTaiwanFuturesLargeTraders:
    @pytest.mark.asyncio
    async def test_large_trader_positions(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_FUTURES_LARGE_TRADERS,
            data_id="TX",
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestTaiwanOptionLargeTraders:
    @pytest.mark.asyncio
    async def test_option_large_traders(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_OPTION_LARGE_TRADERS,
            data_id="TXO",
            start_date=recent_start,
        )
        assert isinstance(data, list)
