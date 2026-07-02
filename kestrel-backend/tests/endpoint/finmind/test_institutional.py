"""Live tests for FinMind institutional/chip datasets.

Covers: TaiwanStockInstitutional, TaiwanStockMargin, TaiwanStockShareholding,
        TaiwanStockHoldingSharesPer, TaiwanStockSecuritiesLending,
        TaiwanstockGovernmentBankBuySell, TaiwanDailyShortSaleBalances

Run: pytest tests/endpoint/finmind/test_institutional.py -v
"""

import pytest

from app.core.constants import FinMindDataset


class TestTaiwanStockInstitutional:
    @pytest.mark.asyncio
    async def test_buy_sell_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock
        assert "buy" in str(row.keys()).lower() or "Buy" in str(row.keys())

    @pytest.mark.asyncio
    async def test_multiple_investor_types(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL,
            data_id=tw_stock,
            start_date=recent_start,
        )
        names = {row.get("name") for row in data}
        assert len(names) > 1


class TestTaiwanStockTotalInstitutional:
    @pytest.mark.asyncio
    async def test_market_wide_institutional(self, provider, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TOTAL_INSTITUTIONAL,
            start_date=recent_start,
        )
        assert len(data) > 0


class TestTaiwanStockMargin:
    @pytest.mark.asyncio
    async def test_margin_short_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MARGIN,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock
        assert "MarginPurchaseBuy" in row or "margin" in str(row.keys()).lower()


class TestTaiwanStockShareholding:
    @pytest.mark.asyncio
    async def test_shareholding_distribution(self, provider, tw_stock, month_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_SHAREHOLDING,
            data_id=tw_stock,
            start_date=month_start,
        )
        assert isinstance(data, list)


class TestTaiwanStockHoldingSharesPer:
    @pytest.mark.asyncio
    async def test_holding_percentage(self, provider, tw_stock, month_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_HOLDING_SHARES_PER,
            data_id=tw_stock,
            start_date=month_start,
        )
        assert isinstance(data, list)


class TestTaiwanStockSecuritiesLending:
    @pytest.mark.asyncio
    async def test_lending_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_SECURITIES_LENDING,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestGovernmentBankBuySell:
    @pytest.mark.asyncio
    async def test_government_bank_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_GOVERNMENT_BANK_BUY_SELL,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestDailyShortSaleBalances:
    @pytest.mark.asyncio
    async def test_short_sale_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_DAILY_SHORT_SALE_BALANCES,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert isinstance(data, list)
