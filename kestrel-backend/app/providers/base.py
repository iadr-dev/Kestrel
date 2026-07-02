from datetime import date
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MarketDataProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def priority(self) -> int: ...

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...

    async def health_check(self) -> dict[str, Any]: ...

    async def supports_dataset(self, dataset: str) -> bool: ...

    async def fetch_dataset(
        self,
        dataset: str,
        *,
        data_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]: ...


class ProviderCapability:
    STOCK_PRICE = "stock_price"
    STOCK_INFO = "stock_info"
    INSTITUTIONAL = "institutional"
    FUNDAMENTAL = "fundamental"
    DERIVATIVE = "derivative"
    REAL_TIME = "real_time"
    INTERNATIONAL = "international"
    MACRO = "macro"
    CONVERTIBLE_BOND = "convertible_bond"
    NEWS = "news"
