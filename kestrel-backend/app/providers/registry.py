from collections import defaultdict
from typing import Any

from app.core.exceptions import ProviderError
from app.providers.base import MarketDataProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}
        self._capability_map: dict[str, list[MarketDataProvider]] = defaultdict(list)

    def register(self, provider: MarketDataProvider, capabilities: list[str]) -> None:
        self._providers[provider.name] = provider
        for cap in capabilities:
            self._capability_map[cap].append(provider)
            self._capability_map[cap].sort(key=lambda p: p.priority)

    def get_provider(self, name: str) -> MarketDataProvider:
        if name not in self._providers:
            raise ProviderError(f"Provider '{name}' not registered")
        return self._providers[name]

    def get_for_capability(self, capability: str) -> list[MarketDataProvider]:
        return self._capability_map.get(capability, [])

    def get_primary(self, capability: str) -> MarketDataProvider:
        providers = self.get_for_capability(capability)
        if not providers:
            raise ProviderError(f"No provider registered for capability '{capability}'")
        return providers[0]

    @property
    def all_providers(self) -> dict[str, MarketDataProvider]:
        return self._providers.copy()

    async def health_check_all(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
        return results
