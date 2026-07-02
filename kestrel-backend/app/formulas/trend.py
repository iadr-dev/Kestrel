import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator


def _ema_array(data: NDArray[np.float64], period: int) -> NDArray[np.float64]:
    result = np.full_like(data, np.nan)
    if len(data) < period:
        return result
    multiplier = 2.0 / (period + 1)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


@register_indicator("macd")
def macd(
    close: NDArray[np.float64],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """MACD (Moving Average Convergence Divergence)."""
    ema_fast = _ema_array(close, fast)
    ema_slow = _ema_array(close, slow)

    dif = ema_fast - ema_slow
    dem = _ema_array(dif[~np.isnan(dif)], signal)

    signal_line = np.full_like(close, np.nan)
    valid_start = slow - 1 + signal - 1
    if len(dem) > 0 and valid_start < len(close):
        signal_line[valid_start: valid_start + len(dem)] = dem[:len(close) - valid_start]

    histogram = dif - signal_line

    return {"dif": dif, "dem": signal_line, "histogram": histogram}
