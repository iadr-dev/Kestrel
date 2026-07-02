import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator


@register_indicator("sma")
def sma(close: NDArray[np.float64], period: int = 20, **_: object) -> dict[str, NDArray[np.float64]]:
    result = np.full_like(close, np.nan)
    if len(close) >= period:
        cumsum = np.cumsum(close)
        cumsum[period:] = cumsum[period:] - cumsum[:-period]
        result[period - 1:] = cumsum[period - 1:] / period
    return {"sma": result}


@register_indicator("ema")
def ema(close: NDArray[np.float64], period: int = 20, **_: object) -> dict[str, NDArray[np.float64]]:
    result = np.full_like(close, np.nan)
    if len(close) < period:
        return {"ema": result}
    multiplier = 2.0 / (period + 1)
    result[period - 1] = np.mean(close[:period])
    for i in range(period, len(close)):
        result[i] = (close[i] - result[i - 1]) * multiplier + result[i - 1]
    return {"ema": result}


@register_indicator("ma")
def ma(close: NDArray[np.float64], periods: list[int] | None = None, **_: object) -> dict[str, NDArray[np.float64]]:
    """Multiple SMAs at once (MA5, MA10, MA20, MA60)."""
    if periods is None:
        periods = [5, 10, 20, 60]
    results: dict[str, NDArray[np.float64]] = {}
    for p in periods:
        result = np.full_like(close, np.nan)
        if len(close) >= p:
            cumsum = np.cumsum(close)
            cumsum[p:] = cumsum[p:] - cumsum[:-p]
            result[p - 1:] = cumsum[p - 1:] / p
        results[f"ma{p}"] = result
    return results
