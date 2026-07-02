"""Live tests for FinMind stock price datasets.

Covers: TaiwanStockPrice, TaiwanStockPriceAdj, TaiwanStockPER,
        TaiwanStockKBar, TaiwanStockWeekPrice, TaiwanStockMonthPrice,
        TaiwanStockDayTrading, TaiwanStockInfo, TaiwanStockTradingDate

Run: pytest tests/endpoint/finmind/test_stock_price.py -v
"""

from datetime import date, timedelta

import pytest

from app.core.constants import FinMindDataset


class TestTaiwanStockPrice:
    @pytest.mark.asyncio
    async def test_returns_ohlcv(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock
        assert "date" in row
        assert "open" in row
        assert "close" in row
        assert "max" in row or "high" in row
        assert "min" in row or "low" in row
        assert "Trading_Volume" in row

    @pytest.mark.asyncio
    async def test_volume_positive(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=tw_stock,
            start_date=recent_start,
        )
        for row in data:
            assert row["Trading_Volume"] > 0

    @pytest.mark.asyncio
    async def test_date_range(self, provider, tw_stock):
        start = date.today() - timedelta(days=5)
        end = date.today()
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=tw_stock,
            start_date=start,
            end_date=end,
        )
        assert isinstance(data, list)
        for row in data:
            assert start.isoformat() <= row["date"] <= end.isoformat()


class TestTaiwanStockPriceAdj:
    @pytest.mark.asyncio
    async def test_adjusted_prices(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE_ADJ,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        assert data[0]["stock_id"] == tw_stock


class TestTaiwanStockPER:
    @pytest.mark.asyncio
    async def test_returns_pe_data(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PER,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert len(data) > 0
        row = data[0]
        assert row["stock_id"] == tw_stock
        assert "PER" in row or "per" in str(row.keys()).lower()


class TestTaiwanStockKBar:
    @pytest.mark.asyncio
    async def test_intraday_kbar(self, provider, tw_stock):
        last_friday = date.today() - timedelta(days=(date.today().weekday() - 4) % 7)
        if last_friday > date.today():
            last_friday -= timedelta(days=7)
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_KBAR,
            data_id=tw_stock,
            start_date=last_friday,
        )
        assert isinstance(data, list)


class TestTaiwanStockWeekPrice:
    @pytest.mark.asyncio
    async def test_weekly_prices(self, provider, tw_stock, month_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_WEEK_PRICE,
            data_id=tw_stock,
            start_date=month_start,
        )
        assert isinstance(data, list)


class TestTaiwanStockMonthPrice:
    @pytest.mark.asyncio
    async def test_monthly_prices(self, provider, tw_stock, quarter_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MONTH_PRICE,
            data_id=tw_stock,
            start_date=quarter_start,
        )
        assert isinstance(data, list)


class TestTaiwanStockDayTrading:
    @pytest.mark.asyncio
    async def test_day_trading_volume(self, provider, tw_stock, recent_start):
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_DAY_TRADING,
            data_id=tw_stock,
            start_date=recent_start,
        )
        assert isinstance(data, list)


class TestTaiwanStockInfo:
    @pytest.mark.asyncio
    async def test_returns_all_stocks(self, provider):
        data = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        assert len(data) > 500
        tsmc = [s for s in data if s.get("stock_id") == "2330"]
        assert len(tsmc) >= 1
        assert tsmc[0]["stock_name"] == "台積電"

    @pytest.mark.asyncio
    async def test_has_industry_category(self, provider):
        data = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        tsmc = next(s for s in data if s.get("stock_id") == "2330")
        assert "industry_category" in tsmc


class TestTaiwanStockTradingDate:
    @pytest.mark.asyncio
    async def test_returns_trading_dates(self, provider):
        data = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_TRADING_DATE)
        assert len(data) > 100
        assert "date" in data[0]
