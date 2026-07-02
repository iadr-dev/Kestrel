import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator


@register_indicator("obv")
def obv(
    close: NDArray[np.float64],
    volume: NDArray[np.float64] | None = None,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """On-Balance Volume."""
    if volume is None:
        return {"obv": np.zeros_like(close)}

    n = len(close)
    result = np.zeros(n)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            result[i] = result[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            result[i] = result[i - 1] - volume[i]
        else:
            result[i] = result[i - 1]
    return {"obv": result}


@register_indicator("vwap")
def vwap(
    close: NDArray[np.float64],
    high: NDArray[np.float64] | None = None,
    low: NDArray[np.float64] | None = None,
    volume: NDArray[np.float64] | None = None,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """Volume Weighted Average Price (cumulative)."""
    if volume is None or high is None or low is None:
        return {"vwap": close.copy()}

    typical_price = (high + low + close) / 3.0
    cum_vol = np.cumsum(volume)
    cum_tp_vol = np.cumsum(typical_price * volume)
    result = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
    return {"vwap": result}
