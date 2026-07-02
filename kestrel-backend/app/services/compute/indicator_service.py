from typing import Any

from app.formulas import IndicatorRegistry, compute_indicators


class IndicatorService:
    def list_indicators(self) -> list[str]:
        return IndicatorRegistry.list_available()

    def compute(
        self,
        close: list[float],
        high: list[float] | None = None,
        low: list[float] | None = None,
        volume: list[int] | None = None,
        indicators: list[dict[str, Any]] | None = None,
        open_: list[float] | None = None,
    ) -> dict[str, dict[str, list[float | None]]]:
        return compute_indicators(
            close=close, high=high, low=low, volume=volume, indicators=indicators, open_=open_
        )
