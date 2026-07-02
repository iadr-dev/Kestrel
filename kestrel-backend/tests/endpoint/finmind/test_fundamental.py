"""Live tests for FinMind fundamental datasets.

Covers: TaiwanStockMonthRevenue, TaiwanStockFinancialStatements,
        TaiwanStockBalanceSheet, TaiwanStockCashFlowsStatement,
        TaiwanStockDividend, TaiwanStockDividendResult,
        TaiwanStockMarketValue, TaiwanStockCapitalReduction

Run: pytest tests/endpoint/finmind/test_fundamental.py -v
"""

from datetime import date

import pytest

from app.core.constants import FinMindDataset


class TestTaiwanStockMonthRevenue:
    @pytest.mark.asyncio
    async def test_returns_revenue(self, provider, tw_stock, quarter_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MONTH_REVENUE,
            data_id=tw_stock,
            start_date=quarter_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock
        assert "revenue" in row
        assert row["revenue"] > 0

    @pytest.mark.asyncio
    async def test_has_date(self, provider, tw_stock, quarter_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MONTH_REVENUE,
            data_id=tw_stock,
            start_date=quarter_start,
        )
        assert "date" in data[0]


class TestTaiwanStockFinancialStatements:
    @pytest.mark.asyncio
    async def test_returns_statements(self, provider, tw_stock, year_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_FINANCIAL_STATEMENTS,
            data_id=tw_stock,
            start_date=year_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock

    @pytest.mark.asyncio
    async def test_multiple_types(self, provider, tw_stock, year_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_FINANCIAL_STATEMENTS,
            data_id=tw_stock,
            start_date=year_start,
        )
        types = {row.get("type") for row in data}
        assert len(types) > 1


class TestTaiwanStockBalanceSheet:
    @pytest.mark.asyncio
    async def test_returns_balance_sheet(self, provider, tw_stock, year_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_BALANCE_SHEET,
            data_id=tw_stock,
            start_date=year_start,
        )
        assert len(data) > 0
        assert data[0]["stock_id"] == tw_stock


class TestTaiwanStockCashFlows:
    @pytest.mark.asyncio
    async def test_returns_cash_flows(self, provider, tw_stock, year_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_CASH_FLOWS,
            data_id=tw_stock,
            start_date=year_start,
        )
        assert len(data) > 0
        assert data[0]["stock_id"] == tw_stock


class TestTaiwanStockDividend:
    @pytest.mark.asyncio
    async def test_returns_dividend_history(self, provider, tw_stock):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_DIVIDEND,
            data_id=tw_stock,
            start_date=date(2020, 1, 1),
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock

    @pytest.mark.asyncio
    async def test_dividend_result(self, provider, tw_stock):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_DIVIDEND_RESULT,
            data_id=tw_stock,
            start_date=date(2020, 1, 1),
        )
        assert isinstance(data, list)


class TestTaiwanStockMarketValue:
    @pytest.mark.asyncio
    async def test_returns_market_value(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MARKET_VALUE,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        assert data[0]["stock_id"] == tw_stock
