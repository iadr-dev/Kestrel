from datetime import date
from typing import Any, cast

from app.core.constants import FinMindDataset
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.registry import ProviderRegistry


class MarketService:
    def __init__(self, registry: ProviderRegistry, cache: CacheBackend) -> None:
        self._registry = registry
        self._cache = cache

    async def get_taiex(self, trade_date: date) -> list[dict[str, Any]]:
        cache_key = build_cache_key("market", "taiex", date=str(trade_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("stock_price")

        # TaiwanVariousIndicators5Seconds is an INTRADAY feed: it's empty on a
        # non-trading `trade_date` (weekend / holiday) and before the session
        # opens. Callers (e.g. the macro marquee) pass a fixed date that is often
        # not a trading day, which left TAIEX showing "—". Walk back up to 8 days
        # to the most recent session with data so the value is always populated;
        # the last row of that session is the day's close. Same walk-back pattern
        # as get_price_limits / the sector-change endpoint.
        from datetime import timedelta

        data: list[dict[str, Any]] = []
        for offset in range(8):
            d = trade_date - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            data = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_VARIOUS_INDICATORS_5SEC,
                start_date=d,
            )
            if data:
                break

        await self._cache.set(cache_key, data, ttl=300)
        return data

    async def get_every_5sec_index(self, trade_date: date) -> list[dict[str, Any]]:
        cache_key = build_cache_key("market", "5sec_index", date=str(trade_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("stock_price")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_EVERY_5SEC_INDEX,
            start_date=trade_date,
        )
        # 60s (was 300s) so the 資金流向 view, which polls every 60s while the market is
        # open, gets genuinely fresh intraday rotation rather than 5-min-stale snapshots.
        await self._cache.set(cache_key, data, ttl=60)
        return data

    async def get_order_book_stats(self, trade_date: date) -> list[dict[str, Any]]:
        cache_key = build_cache_key("market", "order_book", date=str(trade_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("stock_price")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_STATISTICS_ORDER_BOOK,
            start_date=trade_date,
        )
        await self._cache.set(cache_key, data, ttl=900)
        return data

    async def get_total_return_index(
        self, data_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("market", "total_return", data_id=data_id, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("stock_price")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TOTAL_RETURN_INDEX,
            data_id=data_id,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=300)
        return data
