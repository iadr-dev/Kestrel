"""Candlestick pattern detection — 24 patterns across single/multi-candle categories
(includes hanging man, three-inside up/down, and rising/falling three methods).

Architecture:
- Each pattern is a pure function: (open, high, low, close arrays) → signal array
- Patterns registered via @register_indicator for the common "candlestick" entry point
- Individual patterns also callable directly for targeted analysis
- Signal values: +1 bullish, -1 bearish, 0 neutral/no pattern

Detection thresholds (configurable):
- DOJI_BODY_RATIO: 0.1 (body < 10% of range)
- SMALL_BODY_RATIO: 0.3 (body < 30% of range)
- LONG_BODY_RATIO: 0.6 (body > 60% of range)
- SHADOW_MULTIPLIER: 2.0 (shadow must be 2x body for hammer/star)
"""

import numpy as np
from numpy.typing import NDArray

from app.formulas.base import register_indicator

# --- Thresholds ---
DOJI_BODY_RATIO = 0.1
SMALL_BODY_RATIO = 0.3
LONG_BODY_RATIO = 0.6
SHADOW_MULTIPLIER = 2.0
MARUBOZU_WICK_RATIO = 0.05
ENGULF_MIDPOINT_RATIO = 0.5


# --- Utility functions ---

def _body(open_arr: NDArray[np.float64], close_arr: NDArray[np.float64]) -> NDArray[np.float64]:
    """Signed body: positive = bullish, negative = bearish."""
    return close_arr - open_arr


def _body_len(open_arr: NDArray[np.float64], close_arr: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.abs(close_arr - open_arr)


def _range(high_arr: NDArray[np.float64], low_arr: NDArray[np.float64]) -> NDArray[np.float64]:
    r = high_arr - low_arr
    r[r == 0] = 1e-10
    return r


def _upper_shadow(
    open_arr: NDArray[np.float64], high_arr: NDArray[np.float64], close_arr: NDArray[np.float64]
) -> NDArray[np.float64]:
    return high_arr - np.maximum(open_arr, close_arr)


def _lower_shadow(
    open_arr: NDArray[np.float64], low_arr: NDArray[np.float64], close_arr: NDArray[np.float64]
) -> NDArray[np.float64]:
    return np.minimum(open_arr, close_arr) - low_arr


def _body_ratio(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    return _body_len(open_arr, close_arr) / _range(high_arr, low_arr)


def _is_bullish(open_arr: NDArray[np.float64], close_arr: NDArray[np.float64]) -> NDArray[np.bool_]:
    return close_arr > open_arr


def _is_bearish(open_arr: NDArray[np.float64], close_arr: NDArray[np.float64]) -> NDArray[np.bool_]:
    return open_arr > close_arr


# ═══════════════════════════════════════════════════════════════════
# Single-Candle Patterns
# ═══════════════════════════════════════════════════════════════════

def detect_doji(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Doji: body < 10% of range. Indecision signal."""
    ratio = _body_ratio(open_arr, high_arr, low_arr, close_arr)
    return (ratio < DOJI_BODY_RATIO).astype(np.float64)


def detect_dragonfly_doji(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Dragonfly Doji: doji with long lower shadow, minimal upper shadow. Bullish."""
    ratio = _body_ratio(open_arr, high_arr, low_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    rng = _range(high_arr, low_arr)
    return ((ratio < DOJI_BODY_RATIO) & (lower > rng * 0.6) & (upper < rng * 0.1)).astype(np.float64)


def detect_gravestone_doji(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Gravestone Doji: doji with long upper shadow, minimal lower shadow. Bearish."""
    ratio = _body_ratio(open_arr, high_arr, low_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    rng = _range(high_arr, low_arr)
    return -((ratio < DOJI_BODY_RATIO) & (upper > rng * 0.6) & (lower < rng * 0.1)).astype(np.float64)


def detect_hammer(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Hammer: small body at top, lower shadow >= 2x body, upper shadow small. Bullish reversal."""
    bl = _body_len(open_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    return ((lower >= SHADOW_MULTIPLIER * bl) & (upper <= bl) & (bl > 0)).astype(np.float64)


def detect_inverted_hammer(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Inverted Hammer: small body at bottom, upper shadow >= 2x body. Bullish reversal."""
    bl = _body_len(open_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    return ((upper >= SHADOW_MULTIPLIER * bl) & (lower <= bl) & (bl > 0)).astype(np.float64)


def detect_shooting_star(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Shooting Star: same shape as inverted hammer but bearish context. Bearish reversal."""
    bl = _body_len(open_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    bearish = _is_bearish(open_arr, close_arr)
    return -((upper >= SHADOW_MULTIPLIER * bl) & (lower <= bl) & bearish & (bl > 0)).astype(np.float64)


def detect_marubozu(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Marubozu: no/tiny shadows. Strong momentum. +1 bullish, -1 bearish."""
    bl = _body_len(open_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    no_shadows = (upper <= bl * MARUBOZU_WICK_RATIO) & (lower <= bl * MARUBOZU_WICK_RATIO) & (bl > 0)
    bullish = _is_bullish(open_arr, close_arr)
    signal = np.zeros(len(open_arr))
    signal[no_shadows & bullish] = 1
    signal[no_shadows & ~bullish] = -1
    return signal


def detect_spinning_top(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Spinning Top: small body with upper and lower shadows. Indecision."""
    ratio = _body_ratio(open_arr, high_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    bl = _body_len(open_arr, close_arr)
    return ((ratio > DOJI_BODY_RATIO) & (ratio < SMALL_BODY_RATIO) & (upper > bl) & (lower > bl)).astype(np.float64) * 0


# ═══════════════════════════════════════════════════════════════════
# Two-Candle Patterns
# ═══════════════════════════════════════════════════════════════════

def detect_bullish_engulfing(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Bullish Engulfing: bearish candle fully engulfed by next bullish candle."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(1, n):
        prev_bearish = open_arr[i-1] > close_arr[i-1]
        curr_bullish = close_arr[i] > open_arr[i]
        engulfs = close_arr[i] > open_arr[i-1] and open_arr[i] < close_arr[i-1]
        if prev_bearish and curr_bullish and engulfs:
            signal[i] = 1
    return signal


def detect_bearish_engulfing(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Bearish Engulfing: bullish candle fully engulfed by next bearish candle."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(1, n):
        prev_bullish = close_arr[i-1] > open_arr[i-1]
        curr_bearish = open_arr[i] > close_arr[i]
        engulfs = open_arr[i] > close_arr[i-1] and close_arr[i] < open_arr[i-1]
        if prev_bullish and curr_bearish and engulfs:
            signal[i] = -1
    return signal


def detect_piercing_line(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Piercing Line: bearish → bullish that opens below prior low, closes above 50% of prior body."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(1, n):
        prev_bearish = open_arr[i-1] > close_arr[i-1]
        curr_bullish = close_arr[i] > open_arr[i]
        opens_below = open_arr[i] < low_arr[i-1]
        midpoint = (open_arr[i-1] + close_arr[i-1]) / 2
        closes_above_mid = close_arr[i] > midpoint
        if prev_bearish and curr_bullish and opens_below and closes_above_mid:
            signal[i] = 1
    return signal


def detect_dark_cloud_cover(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Dark Cloud Cover: bullish → bearish that opens above prior high, closes below 50% of prior body."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(1, n):
        prev_bullish = close_arr[i-1] > open_arr[i-1]
        curr_bearish = open_arr[i] > close_arr[i]
        opens_above = open_arr[i] > high_arr[i-1]
        midpoint = (open_arr[i-1] + close_arr[i-1]) / 2
        closes_below_mid = close_arr[i] < midpoint
        if prev_bullish and curr_bearish and opens_above and closes_below_mid:
            signal[i] = -1
    return signal


def detect_harami(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Harami: small candle contained within prior large candle's body. +1 bullish, -1 bearish."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(1, n):
        prev_top = max(open_arr[i-1], close_arr[i-1])
        prev_bottom = min(open_arr[i-1], close_arr[i-1])
        curr_top = max(open_arr[i], close_arr[i])
        curr_bottom = min(open_arr[i], close_arr[i])
        contained = curr_top <= prev_top and curr_bottom >= prev_bottom
        prev_large = _body_ratio(
            np.array([open_arr[i-1]]), np.array([high_arr[i-1]]),
            np.array([low_arr[i-1]]), np.array([close_arr[i-1]])
        )[0] > LONG_BODY_RATIO
        if contained and prev_large:
            if open_arr[i-1] > close_arr[i-1]:
                signal[i] = 1
            else:
                signal[i] = -1
    return signal


def detect_tweezer_tops(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Tweezer Tops: two candles with nearly matching highs. Bearish reversal."""
    n = len(open_arr)
    signal = np.zeros(n)
    avg_range = np.mean(_range(high_arr, low_arr))
    tolerance = avg_range * 0.02
    for i in range(1, n):
        matching_highs = abs(high_arr[i] - high_arr[i-1]) <= tolerance
        prev_bullish = close_arr[i-1] > open_arr[i-1]
        curr_bearish = open_arr[i] > close_arr[i]
        if matching_highs and prev_bullish and curr_bearish:
            signal[i] = -1
    return signal


def detect_tweezer_bottoms(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Tweezer Bottoms: two candles with nearly matching lows. Bullish reversal."""
    n = len(open_arr)
    signal = np.zeros(n)
    avg_range = np.mean(_range(high_arr, low_arr))
    tolerance = avg_range * 0.02
    for i in range(1, n):
        matching_lows = abs(low_arr[i] - low_arr[i-1]) <= tolerance
        prev_bearish = open_arr[i-1] > close_arr[i-1]
        curr_bullish = close_arr[i] > open_arr[i]
        if matching_lows and prev_bearish and curr_bullish:
            signal[i] = 1
    return signal


# ═══════════════════════════════════════════════════════════════════
# Three-Candle Patterns
# ═══════════════════════════════════════════════════════════════════

def detect_morning_star(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Morning Star: large bearish → small body (star) → large bullish closing above midpoint of first."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        r1 = high_arr[i-2] - low_arr[i-2]
        r3 = high_arr[i] - low_arr[i]
        if r1 == 0 or r3 == 0:
            continue
        first_bearish = open_arr[i-2] > close_arr[i-2] and abs(open_arr[i-2] - close_arr[i-2]) / r1 > LONG_BODY_RATIO
        star_small = _body_ratio(
            np.array([open_arr[i-1]]), np.array([high_arr[i-1]]),
            np.array([low_arr[i-1]]), np.array([close_arr[i-1]])
        )[0] < SMALL_BODY_RATIO
        third_bullish = close_arr[i] > open_arr[i] and abs(close_arr[i] - open_arr[i]) / r3 > LONG_BODY_RATIO
        midpoint = (open_arr[i-2] + close_arr[i-2]) / 2
        closes_above_mid = close_arr[i] > midpoint
        if first_bearish and star_small and third_bullish and closes_above_mid:
            signal[i] = 1
    return signal


def detect_evening_star(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Evening Star: large bullish → small body (star) → large bearish closing below midpoint of first."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        r1 = high_arr[i-2] - low_arr[i-2]
        r3 = high_arr[i] - low_arr[i]
        if r1 == 0 or r3 == 0:
            continue
        first_bullish = close_arr[i-2] > open_arr[i-2] and abs(close_arr[i-2] - open_arr[i-2]) / r1 > LONG_BODY_RATIO
        star_small = _body_ratio(
            np.array([open_arr[i-1]]), np.array([high_arr[i-1]]),
            np.array([low_arr[i-1]]), np.array([close_arr[i-1]])
        )[0] < SMALL_BODY_RATIO
        third_bearish = open_arr[i] > close_arr[i] and abs(open_arr[i] - close_arr[i]) / r3 > LONG_BODY_RATIO
        midpoint = (open_arr[i-2] + close_arr[i-2]) / 2
        closes_below_mid = close_arr[i] < midpoint
        if first_bullish and star_small and third_bearish and closes_below_mid:
            signal[i] = -1
    return signal


def detect_three_white_soldiers(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Three White Soldiers: three consecutive long bullish candles, each closing higher."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        all_bullish = all(close_arr[i-j] > open_arr[i-j] for j in range(3))
        each_higher = close_arr[i] > close_arr[i-1] > close_arr[i-2]
        # Each soldier should open within the prior candle's real body (classic
        # Three White Soldiers criterion) — guards against gap-driven false signals.
        opens_within_body = all(
            min(open_arr[i-j], close_arr[i-j]) <= open_arr[i-j+1] <= max(open_arr[i-j], close_arr[i-j])
            for j in range(1, 3)
            if i-j+1 < n
        )
        if all_bullish and each_higher and opens_within_body:
            signal[i] = 1
    return signal


def detect_three_black_crows(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Three Black Crows: three consecutive long bearish candles, each closing lower."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        all_bearish = all(open_arr[i-j] > close_arr[i-j] for j in range(3))
        each_lower = close_arr[i] < close_arr[i-1] < close_arr[i-2]
        if all_bearish and each_lower:
            signal[i] = -1
    return signal


def detect_hanging_man(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Hanging Man: hammer shape (small body, long lower shadow) appearing after an
    uptrend. Bearish reversal. Distinguished from a hammer by the prior trend —
    here the 3 prior closes are rising."""
    n = len(open_arr)
    signal = np.zeros(n)
    bl = _body_len(open_arr, close_arr)
    lower = _lower_shadow(open_arr, low_arr, close_arr)
    upper = _upper_shadow(open_arr, high_arr, close_arr)
    for i in range(3, n):
        hammer_shape = lower[i] >= SHADOW_MULTIPLIER * bl[i] and upper[i] <= bl[i] and bl[i] > 0
        prior_uptrend = close_arr[i-1] > close_arr[i-2] > close_arr[i-3]
        if hammer_shape and prior_uptrend:
            signal[i] = -1
    return signal


def detect_three_inside_up(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Three Inside Up: bullish harami (large bearish + contained small body) then a
    third bullish candle closing above the first candle's open. Confirmed reversal."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        first_bearish = open_arr[i-2] > close_arr[i-2] and _body_ratio(
            np.array([open_arr[i-2]]), np.array([high_arr[i-2]]),
            np.array([low_arr[i-2]]), np.array([close_arr[i-2]]),
        )[0] > LONG_BODY_RATIO
        contained = (
            max(open_arr[i-1], close_arr[i-1]) <= max(open_arr[i-2], close_arr[i-2])
            and min(open_arr[i-1], close_arr[i-1]) >= min(open_arr[i-2], close_arr[i-2])
        )
        third_confirms = close_arr[i] > open_arr[i] and close_arr[i] > open_arr[i-2]
        if first_bearish and contained and third_confirms:
            signal[i] = 1
    return signal


def detect_three_inside_down(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Three Inside Down: bearish harami (large bullish + contained small body) then a
    third bearish candle closing below the first candle's open. Confirmed reversal."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(2, n):
        first_bullish = close_arr[i-2] > open_arr[i-2] and _body_ratio(
            np.array([open_arr[i-2]]), np.array([high_arr[i-2]]),
            np.array([low_arr[i-2]]), np.array([close_arr[i-2]]),
        )[0] > LONG_BODY_RATIO
        contained = (
            max(open_arr[i-1], close_arr[i-1]) <= max(open_arr[i-2], close_arr[i-2])
            and min(open_arr[i-1], close_arr[i-1]) >= min(open_arr[i-2], close_arr[i-2])
        )
        third_confirms = open_arr[i] > close_arr[i] and close_arr[i] < open_arr[i-2]
        if first_bullish and contained and third_confirms:
            signal[i] = -1
    return signal


def detect_rising_three_methods(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Rising Three Methods: long bullish candle, 3 small bearish candles staying
    within its range, then another long bullish candle closing at a new high.
    Bullish continuation."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(4, n):
        first_bull = close_arr[i-4] > open_arr[i-4] and _body_ratio(
            np.array([open_arr[i-4]]), np.array([high_arr[i-4]]),
            np.array([low_arr[i-4]]), np.array([close_arr[i-4]]),
        )[0] > LONG_BODY_RATIO
        middle_in_range = all(
            high_arr[i-3+k] <= high_arr[i-4] and low_arr[i-3+k] >= low_arr[i-4]
            for k in range(3)
        )
        middle_small = all(
            _body_len(np.array([open_arr[i-3+k]]), np.array([close_arr[i-3+k]]))[0]
            < _body_len(np.array([open_arr[i-4]]), np.array([close_arr[i-4]]))[0]
            for k in range(3)
        )
        last_bull = close_arr[i] > open_arr[i] and close_arr[i] > close_arr[i-4]
        if first_bull and middle_in_range and middle_small and last_bull:
            signal[i] = 1
    return signal


def detect_falling_three_methods(
    open_arr: NDArray[np.float64],
    high_arr: NDArray[np.float64],
    low_arr: NDArray[np.float64],
    close_arr: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Falling Three Methods: long bearish candle, 3 small bullish candles staying
    within its range, then another long bearish candle closing at a new low.
    Bearish continuation."""
    n = len(open_arr)
    signal = np.zeros(n)
    for i in range(4, n):
        first_bear = open_arr[i-4] > close_arr[i-4] and _body_ratio(
            np.array([open_arr[i-4]]), np.array([high_arr[i-4]]),
            np.array([low_arr[i-4]]), np.array([close_arr[i-4]]),
        )[0] > LONG_BODY_RATIO
        middle_in_range = all(
            high_arr[i-3+k] <= high_arr[i-4] and low_arr[i-3+k] >= low_arr[i-4]
            for k in range(3)
        )
        middle_small = all(
            _body_len(np.array([open_arr[i-3+k]]), np.array([close_arr[i-3+k]]))[0]
            < _body_len(np.array([open_arr[i-4]]), np.array([close_arr[i-4]]))[0]
            for k in range(3)
        )
        last_bear = open_arr[i] > close_arr[i] and close_arr[i] < close_arr[i-4]
        if first_bear and middle_in_range and middle_small and last_bear:
            signal[i] = -1
    return signal


# ═══════════════════════════════════════════════════════════════════
# Composite Pattern Detector (registered as "candlestick" indicator)
# ═══════════════════════════════════════════════════════════════════

ALL_PATTERNS = {
    # Single-candle
    "doji": detect_doji,
    "dragonfly_doji": detect_dragonfly_doji,
    "gravestone_doji": detect_gravestone_doji,
    "hammer": detect_hammer,
    "inverted_hammer": detect_inverted_hammer,
    "shooting_star": detect_shooting_star,
    "marubozu": detect_marubozu,
    "spinning_top": detect_spinning_top,
    # Two-candle
    "bullish_engulfing": detect_bullish_engulfing,
    "bearish_engulfing": detect_bearish_engulfing,
    "piercing_line": detect_piercing_line,
    "dark_cloud_cover": detect_dark_cloud_cover,
    "harami": detect_harami,
    "tweezer_tops": detect_tweezer_tops,
    "tweezer_bottoms": detect_tweezer_bottoms,
    # Single-candle (trend-dependent)
    "hanging_man": detect_hanging_man,
    # Three-candle
    "morning_star": detect_morning_star,
    "evening_star": detect_evening_star,
    "three_white_soldiers": detect_three_white_soldiers,
    "three_black_crows": detect_three_black_crows,
    "three_inside_up": detect_three_inside_up,
    "three_inside_down": detect_three_inside_down,
    # Five-candle continuation
    "rising_three_methods": detect_rising_three_methods,
    "falling_three_methods": detect_falling_three_methods,
}


@register_indicator("candlestick")
def candlestick_patterns(
    close: NDArray[np.float64],
    high: NDArray[np.float64] | None = None,
    low: NDArray[np.float64] | None = None,
    volume: NDArray[np.float64] | None = None,
    patterns: list[str] | None = None,
    open_: NDArray[np.float64] | None = None,
    **_: object,
) -> dict[str, NDArray[np.float64]]:
    """Detect candlestick patterns across OHLC data.

    Args:
        close: Close prices (required)
        high: High prices (defaults to close if not provided)
        low: Low prices (defaults to close if not provided)
        patterns: Specific patterns to detect (default: all patterns)

    Returns:
        Dict mapping pattern names to signal arrays (+1 bullish, -1 bearish, 0 none)
        Plus a composite 'signal' key with the strongest signal per bar.
    """
    if high is None:
        high = close
    if low is None:
        low = close

    # Prefer genuine open prices. Only when they're unavailable do we approximate
    # open as the prior close — that approximation invents phantom gap/engulfing
    # patterns on days the stock actually gapped, so real opens are strongly
    # preferred (threaded through from compute_indicators).
    if open_ is not None and len(open_) == len(close):
        open_arr = np.asarray(open_, dtype=np.float64)
    else:
        open_arr = np.roll(close, 1)
        open_arr[0] = close[0]

    selected = patterns if patterns else list(ALL_PATTERNS.keys())
    results: dict[str, NDArray[np.float64]] = {}

    for name in selected:
        fn = ALL_PATTERNS.get(name)
        if fn:
            results[name] = fn(open_arr, high, low, close)

    composite = np.zeros(len(close))
    for arr in results.values():
        stronger = np.abs(arr) > np.abs(composite)
        composite[stronger] = arr[stronger]
    results["signal"] = composite

    return results
