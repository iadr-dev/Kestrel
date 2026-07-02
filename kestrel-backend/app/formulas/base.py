"""Technical indicator computation framework."""

from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

IndicatorFn = Callable[..., dict[str, NDArray[np.float64]]]

_REGISTRY: dict[str, IndicatorFn] = {}


def register_indicator(name: str) -> Callable[[IndicatorFn], IndicatorFn]:
    def decorator(fn: IndicatorFn) -> IndicatorFn:
        _REGISTRY[name] = fn
        return fn
    return decorator


class IndicatorRegistry:
    @staticmethod
    def list_available() -> list[str]:
        return list(_REGISTRY.keys())

    @staticmethod
    def compute(name: str, close: NDArray[np.float64], **kwargs: Any) -> dict[str, NDArray[np.float64]]:
        fn = _REGISTRY.get(name)
        if fn is None:
            raise ValueError(f"Unknown indicator: {name}")
        return fn(close=close, **kwargs)


def compute_indicators(
    close: list[float],
    high: list[float] | None = None,
    low: list[float] | None = None,
    volume: list[int] | None = None,
    indicators: list[dict[str, Any]] | None = None,
    open_: list[float] | None = None,
) -> dict[str, dict[str, list[float | None]]]:
    if not indicators:
        return {}

    close_arr = np.array(close, dtype=np.float64)
    high_arr = np.array(high, dtype=np.float64) if high else close_arr
    low_arr = np.array(low, dtype=np.float64) if low else close_arr
    vol_arr = np.array(volume, dtype=np.float64) if volume else np.zeros_like(close_arr)
    # Real open prices when available; candlestick patterns need genuine opens to
    # avoid phantom signals on gap days (else open is derived from prev close).
    open_arr = np.array(open_, dtype=np.float64) if open_ else None

    results: dict[str, dict[str, list[float | None]]] = {}
    for spec in indicators:
        name = spec["name"]
        params = spec.get("params", {})
        fn = _REGISTRY.get(name)
        if fn is None:
            continue
        raw = fn(close=close_arr, high=high_arr, low=low_arr, volume=vol_arr, open_=open_arr, **params)
        results[name] = {
            k: [None if np.isnan(v) else float(v) for v in arr]
            for k, arr in raw.items()
        }
    return results
