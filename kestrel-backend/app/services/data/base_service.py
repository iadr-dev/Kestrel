"""Shared base for the FinMind-backed data services.

Five services (institutional, fundamental, macro, international, derivative) had
an identical `_cached_fetch` (check cache → fetch from the capability's primary
provider → store). This centralizes that so cache policy lives in one place.

Subclasses declare their default provider capability and TTL; everything else is
inherited. Behavior is preserved exactly — each subclass keeps its previous
default TTL and capability.
"""

from typing import Any, cast

from app.providers.cache import CacheBackend
from app.providers.registry import ProviderRegistry


class BaseDataService:
    """Cache-then-fetch base for capability-scoped data services."""

    #: Provider capability this service reads from (e.g. "institutional"). Override.
    provider_capability: str = ""
    #: Default cache TTL in seconds when a call doesn't pass one. Override.
    default_ttl: int = 900

    def __init__(self, registry: ProviderRegistry, cache: CacheBackend) -> None:
        self._registry = registry
        self._cache = cache

    async def _cached_fetch(
        self,
        cache_key: str,
        dataset: str,
        ttl: int | None = None,
        provider_key: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Return cached rows if present, else fetch from the primary provider for
        `provider_key` (default: this service's capability) and cache for `ttl`
        (default: this service's `default_ttl`)."""
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary(provider_key or self.provider_capability)
        data = await provider.fetch_dataset(dataset, **kwargs)
        await self._cache.set(cache_key, data, ttl=ttl if ttl is not None else self.default_ttl)
        return data
