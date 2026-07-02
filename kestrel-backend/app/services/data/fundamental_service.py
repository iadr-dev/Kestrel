from datetime import date
from typing import Any

from app.core.constants import FinMindDataset
from app.providers.cache import build_cache_key
from app.services.data.base_service import BaseDataService


class FundamentalService(BaseDataService):
    provider_capability = "fundamental"
    default_ttl = 3600

    async def get_income_statement(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "income", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_FINANCIAL_STATEMENTS, data_id=stock_id, start_date=start_date)

    async def get_balance_sheet(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "balance", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_BALANCE_SHEET, data_id=stock_id, start_date=start_date)

    async def get_cash_flow(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "cashflow", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_CASH_FLOWS, data_id=stock_id, start_date=start_date)

    async def get_revenue(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "revenue", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_MONTH_REVENUE, data_id=stock_id, start_date=start_date)

    async def get_dividend(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "dividend", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_DIVIDEND, data_id=stock_id, start_date=start_date)

    async def get_dividend_result(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "div_result", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_DIVIDEND_RESULT, data_id=stock_id, start_date=start_date)

    async def get_market_value(self, stock_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "mktcap", stock_id=stock_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_MARKET_VALUE, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_market_value_weight(self, stock_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "mktcap_weight", stock_id=stock_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_MARKET_VALUE_WEIGHT, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_capital_reduction(self, stock_id: str, start_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "cap_red", stock_id=stock_id, start=str(start_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_CAPITAL_REDUCTION, data_id=stock_id, start_date=start_date)

    async def get_delisted(self) -> list[dict[str, Any]]:
        key = build_cache_key("fund", "delisted")
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_DELISTING, ttl=86400)
