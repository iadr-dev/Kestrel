"""FinMind provider — implements MarketDataProvider protocol for all FinMind datasets."""

from datetime import date
from typing import Any

from app.core.config import FinMindTier, Settings
from app.core.constants import FinMindDataset
from app.core.exceptions import TierInsufficientError
from app.core.logging import get_logger
from app.providers.finmind.client import FinMindClient
from app.providers.finmind.datasets import DATASET_META

logger = get_logger(__name__)

TIER_ORDER = {FinMindTier.FREE: 0, FinMindTier.BACKER: 1, FinMindTier.SPONSOR: 2}


class FinMindProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = FinMindClient(settings)
        self._tier = settings.finmind_tier

    @property
    def name(self) -> str:
        return "finmind"

    @property
    def priority(self) -> int:
        return 1

    async def initialize(self) -> None:
        logger.info("finmind_init", tier=self._tier)

    async def close(self) -> None:
        await self._client.close()

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "provider": "finmind",
            "tier": self._tier,
            "rate_limit_remaining": self._client.available_tokens,
            "rate_limit_max": self._settings.finmind_rate_limit,
        }

    async def supports_dataset(self, dataset: str) -> bool:
        meta = DATASET_META.get(dataset)
        if meta is None:
            return False
        return TIER_ORDER.get(self._tier, 0) >= TIER_ORDER.get(meta.tier, 0)

    async def fetch(
        self,
        dataset: str,
        *,
        data_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return await self.fetch_dataset(dataset, data_id=data_id, start_date=start_date, end_date=end_date, **kwargs)

    async def fetch_dataset(
        self,
        dataset: str,
        *,
        data_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self._check_tier(dataset)
        return await self._client.fetch(
            dataset,
            data_id=data_id,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

    def _check_tier(self, dataset: str) -> None:
        meta = DATASET_META.get(dataset)
        if meta is None:
            return
        required = TIER_ORDER.get(meta.tier, 0)
        current = TIER_ORDER.get(self._tier, 0)
        if current < required:
            raise TierInsufficientError(
                message=f"Dataset '{dataset}' requires {meta.tier} tier (current: {self._tier})",
                detail={"dataset": dataset, "required_tier": meta.tier, "current_tier": self._tier},
            )

    # --- Convenience methods for common datasets ---

    async def get_stock_price(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        return await self.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_stock_info(self) -> list[dict[str, Any]]:
        return await self.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)

    async def get_institutional_investors(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        return await self.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_tick_snapshot(self, stock_id: str | None = None) -> list[dict[str, Any]]:
        return await self.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TICK_SNAPSHOT,
            data_id=stock_id,
        )

    async def get_trading_daily_report(
        self, *, data_id: str | None = None, securities_trader_id: str | None = None, report_date: date | None = None
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if securities_trader_id:
            kwargs["securities_trader_id"] = securities_trader_id
        return await self.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TRADING_DAILY_REPORT,
            data_id=data_id,
            start_date=report_date,
            **kwargs,
        )
