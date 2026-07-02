import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator


@register_indicator("kd")
def kd(
    close: NDArray[np.float64],
    high: NDArray[np.float64] | None = None,
    low: NDArray[np.float64] | None = None,
    period: int = 9,
    k_smooth: int = 3,
    d_smooth: int = 3,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """Stochastic KD oscillator."""
    if high is None:
        high = close
    if low is None:
        low = close

    n = len(close)
    rsv = np.full(n, np.nan)

    for i in range(period - 1, n):
        highest = np.max(high[i - period + 1: i + 1])
        lowest = np.min(low[i - period + 1: i + 1])
        if highest == lowest:
            rsv[i] = 50.0
        else:
            rsv[i] = (close[i] - lowest) / (highest - lowest) * 100.0

    k = np.full(n, np.nan)
    d = np.full(n, np.nan)
    start = period - 1
    if start < n:
        k[start] = 50.0
        d[start] = 50.0
        for i in range(start + 1, n):
            k[i] = k[i - 1] * (k_smooth - 1) / k_smooth + rsv[i] / k_smooth
            d[i] = d[i - 1] * (d_smooth - 1) / d_smooth + k[i] / d_smooth

    return {"k": k, "d": d}


@register_indicator("rsi")
def rsi(close: NDArray[np.float64], period: int = 14, **_: object) -> dict[str, NDArray[np.float64]]:
    """Relative Strength Index."""
    n = len(close)
    result = np.full(n, np.nan)
    if n < period + 1:
        return {"rsi": result}

    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - 100.0 / (1.0 + rs)

    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - 100.0 / (1.0 + rs)

    return {"rsi": result}
