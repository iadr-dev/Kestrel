from datetime import date
from typing import Any, cast

from app.core.constants import FinMindDataset
from app.providers.cache import build_cache_key
from app.services.data.base_service import BaseDataService


class MacroService(BaseDataService):
    provider_capability = "macro"
    default_ttl = 21600

    async def get_exchange_rate(
        self, currency: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("macro", "fx", currency=currency, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_EXCHANGE_RATE, data_id=currency, start_date=start_date, end_date=end_date)

    async def get_interest_rate(
        self, country: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "rate", country=country, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.INTEREST_RATE,
            data_id=country,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data

    async def get_gold_price(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "gold", start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.GOLD_PRICE,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data

    async def get_oil_price(
        self, oil_type: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "oil", oil_type=oil_type, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.CRUDE_OIL_PRICES,
            data_id=oil_type,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data

    async def get_bond_yield(
        self, maturity: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "bond", maturity=maturity, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.GOVERNMENT_BONDS_YIELD,
            data_id=maturity,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data

    async def get_fear_greed(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "fear_greed", start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.CNN_FEAR_GREED_INDEX,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data

    async def get_business_indicator(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        cache_key = build_cache_key("macro", "business", start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("macro")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_BUSINESS_INDICATOR,
            start_date=start_date,
            end_date=end_date,
        )
        await self._cache.set(cache_key, data, ttl=21600)
        return data
