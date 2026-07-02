import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator


@register_indicator("bollinger")
def bollinger(
    close: NDArray[np.float64],
    period: int = 20,
    std_dev: float = 2.0,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """Bollinger Bands."""
    n = len(close)
    middle = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    for i in range(period - 1, n):
        window = close[i - period + 1: i + 1]
        m = np.mean(window)
        s = np.std(window, ddof=0)
        middle[i] = m
        upper[i] = m + std_dev * s
        lower[i] = m - std_dev * s

    return {"middle": middle, "upper": upper, "lower": lower}


@register_indicator("atr")
def atr(
    close: NDArray[np.float64],
    high: NDArray[np.float64] | None = None,
    low: NDArray[np.float64] | None = None,
    period: int = 14,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """Average True Range."""
    if high is None:
        high = close
    if low is None:
        low = close

    n = len(close)
    tr = np.full(n, np.nan)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    result = np.full(n, np.nan)
    if n >= period:
        result[period - 1] = np.mean(tr[:period])
        for i in range(period, n):
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period

    return {"atr": result}
