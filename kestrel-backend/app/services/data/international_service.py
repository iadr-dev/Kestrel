from datetime import date
from typing import Any

from app.core.constants import FinMindDataset
from app.providers.cache import build_cache_key
from app.services.data.base_service import BaseDataService


class InternationalService(BaseDataService):
    provider_capability = "international"
    default_ttl = 300

    async def get_us_price(self, stock_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "us_price", id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.US_STOCK_PRICE, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_us_prices_batch(
        self, stock_ids: list[str], start_date: date, end_date: date | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch daily prices for many US tickers in ONE backend request.

        Lets the UI render N sparklines/candles with a single HTTP call instead of
        N concurrent ones (which trip the per-IP rate limiter). Each ticker is still
        a separate FinMind fetch, but those run server-side with bounded concurrency
        against the generous FinMind budget and reuse the per-ticker cache.
        """
        import asyncio

        seen: list[str] = []
        for sid in stock_ids:
            if sid and sid not in seen:
                seen.append(sid)

        # Cap fan-out so we never hammer FinMind even if the caller passes a huge list.
        sem = asyncio.Semaphore(8)

        async def one(sid: str) -> tuple[str, list[dict[str, Any]]]:
            async with sem:
                try:
                    return sid, await self.get_us_price(sid, start_date, end_date)
                except Exception:
                    return sid, []

        pairs = await asyncio.gather(*[one(s) for s in seen])
        return {sid: rows for sid, rows in pairs}

    async def get_us_price_minute(self, stock_id: str, trade_date: date) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "us_min", id=stock_id, date=str(trade_date))
        return await self._cached_fetch(key, FinMindDataset.US_STOCK_PRICE_MINUTE, ttl=60, data_id=stock_id, start_date=trade_date)

    async def get_us_info(self) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "us_info")
        return await self._cached_fetch(key, FinMindDataset.US_STOCK_INFO, ttl=86400)

    async def get_uk_price(self, stock_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "uk_price", id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.UK_STOCK_PRICE, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_europe_price(self, stock_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "eu_price", id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.EUROPE_STOCK_PRICE, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_japan_price(self, stock_id: str, start_date: date, end_date: date | None = None) -> list[dict[str, Any]]:
        key = build_cache_key("intl", "jp_price", id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.JAPAN_STOCK_PRICE, data_id=stock_id, start_date=start_date, end_date=end_date)
