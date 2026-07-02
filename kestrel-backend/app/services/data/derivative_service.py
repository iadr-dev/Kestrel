from datetime import date
from typing import Any

from app.core.constants import FinMindDataset
from app.providers.cache import build_cache_key
from app.services.data.base_service import BaseDataService


class DerivativeService(BaseDataService):
    provider_capability = "derivative"
    default_ttl = 300

    async def get_futures_daily(self, futures_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "futures_daily", id=futures_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_DAILY, data_id=futures_id, start_date=start_date, end_date=end_date)

    async def get_futures_tick(self, futures_id: str, trade_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "futures_tick", id=futures_id, date=str(trade_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_TICK, ttl=60, data_id=futures_id, start_date=trade_date)

    async def get_options_daily(self, option_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "options_daily", id=option_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_DAILY, data_id=option_id, start_date=start_date, end_date=end_date)

    async def get_options_tick(self, option_id: str, trade_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "options_tick", id=option_id, date=str(trade_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_TICK, ttl=60, data_id=option_id, start_date=trade_date)

    async def get_futures_institutional(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "fut_inst", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_futures_institutional_after_hours(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "fut_inst_ah", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_INSTITUTIONAL_AFTER_HOURS, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_options_institutional(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "opt_inst", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_INSTITUTIONAL, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_options_institutional_after_hours(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "opt_inst_ah", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_INSTITUTIONAL_AFTER_HOURS, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_futures_large_traders(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "fut_large", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_LARGE_TRADERS, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_options_large_traders(self, data_id: str | None = None, start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "opt_large", id=data_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_LARGE_TRADERS, ttl=900, data_id=data_id, start_date=start_date, end_date=end_date)

    async def get_futures_spread(self, futures_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "spread", id=futures_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_SPREAD, data_id=futures_id, start_date=start_date, end_date=end_date)

    async def get_futures_settlement(self, futures_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "fut_settle", id=futures_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_SETTLEMENT, data_id=futures_id, start_date=start_date, end_date=end_date)

    async def get_options_settlement(self, option_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "opt_settle", id=option_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTION_SETTLEMENT, data_id=option_id, start_date=start_date, end_date=end_date)

    async def get_futures_snapshot(self, data_id: str | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "fut_snap", id=data_id or "")
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_FUTURES_SNAPSHOT, ttl=60, provider_key="real_time", data_id=data_id)

    async def get_options_snapshot(self, data_id: str | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("deriv", "opt_snap", id=data_id or "")
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_OPTIONS_SNAPSHOT, ttl=60, provider_key="real_time", data_id=data_id)
