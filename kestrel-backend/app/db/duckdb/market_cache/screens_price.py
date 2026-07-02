"""MarketDataCache — price/technical screens.

Single columnar SQL scan over price_daily rather than fetching the whole market
over HTTP and looping in Python — the professional EOD pattern: accumulate daily
bars in the columnar store, then screen with SQL window functions. All restrict to
4-digit numeric TW common-stock IDs and cap to the most recent complete trading day
present in the table. Bound onto MarketDataCache in __init__.py.
"""

from typing import TYPE_CHECKING, Any

from app.db.duckdb.market_cache._sql import ADJ_PRICE_CTE, TW_ID_FILTER

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache


async def screen_strong_n_day(
    self: "MarketDataCache", days: int, min_return_pct: float = 5.0, limit: int = 30
) -> list[dict[str, Any]]:
    """Cumulative return over the last `days` trading bars > threshold."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        windowed AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = ? THEN adj_close END) AS first_adj,
                   COUNT(*) AS n
            FROM recent
            WHERE rn <= ?
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume,
               ROUND((last_adj - first_adj) / first_adj * 100, 2) AS cum_return
        FROM windowed
        WHERE n >= ? AND first_adj > 0
          AND (last_adj - first_adj) / first_adj * 100 > ?
        ORDER BY cum_return DESC
        LIMIT ?
        """,
        [days, days, days, min_return_pct, limit],
    )
    return [
        {"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3], "cum_return": r[4]}
        for r in rows
    ]


async def screen_trend(self: "MarketDataCache", limit: int = 30) -> list[dict[str, Any]]:
    """MA5 > MA20 > MA60 and last close above MA5 (uptrend stack)."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= 5 THEN adj_close END) AS ma5,
                   AVG(CASE WHEN rn <= 20 THEN adj_close END) AS ma20,
                   AVG(CASE WHEN rn <= 60 THEN adj_close END) AS ma60,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= 60 AND last_adj > ma5 AND ma5 > ma20 AND ma20 > ma60
        ORDER BY last_close DESC
        LIMIT ?
        """,
        [limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_ma_reclaim(self: "MarketDataCache", period: int, limit: int = 30) -> list[dict[str, Any]]:
    """站上 MA<period>: price just crossed above its moving average — at/below the
    MA on the prior session, above it on the latest. `ma_today` averages the most
    recent `period` closes (rn 1..period); `ma_prev` averages the prior window
    (rn 2..period+1). Mirrors screen_trend's adjusted-price CTE. period ∈ {5,10,20,60}."""
    if period not in (5, 10, 20, 60):
        return []
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS ma_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS ma_prev,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 2 THEN adj_close END) AS prev_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1 AND prev_adj <= ma_prev AND last_adj > ma_today
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [period, period, period, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_ma_break(self: "MarketDataCache", period: int, limit: int = 30) -> list[dict[str, Any]]:
    """跌破 MA<period>: price just crossed BELOW its moving average — at/above the MA
    on the prior session, below it on the latest. Mirror of screen_ma_reclaim.
    period ∈ {5,10,20,60}."""
    if period not in (5, 10, 20, 60):
        return []
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS ma_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS ma_prev,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 2 THEN adj_close END) AS prev_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1 AND prev_adj >= ma_prev AND last_adj < ma_today
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [period, period, period, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_ma_slope(self: "MarketDataCache", period: int, direction: str, limit: int = 30) -> list[dict[str, Any]]:
    """均線回升 / 回跌: the MA<period> is turning up (today's MA > yesterday's) or down.
    `direction` ∈ {up, down}. Yesterday's MA = the same `period` window shifted one bar
    back (rn 2..period+1). period ∈ {5,10,20,60}."""
    if period not in (5, 10, 20, 60):
        return []
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    cmp = ">" if direction == "up" else "<"
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS ma_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS ma_prev,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1 AND ma_today {cmp} ma_prev
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [period, period, period, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_ma_cross(self: "MarketDataCache", direction: str, fast: int = 5, slow: int = 20, limit: int = 30) -> list[dict[str, Any]]:
    """均線交叉: fast MA crosses the slow MA. `direction` up = golden cross (fast was
    ≤ slow yesterday, > slow today); down = death cross. Defaults MA5×MA20."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    # today/prev windows for both MAs (prev = window shifted back one bar).
    today_cmp, prev_cmp = (">", "<=") if direction == "up" else ("<", ">=")
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS fast_today,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS slow_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS fast_prev,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS slow_prev,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1
          AND fast_today {today_cmp} slow_today
          AND fast_prev {prev_cmp} slow_prev
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [fast, slow, fast, slow, slow, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_long_candle(self: "MarketDataCache", direction: str, period: int = 20, min_body_pct: float = 4.0, limit: int = 30) -> list[dict[str, Any]]:
    """長紅突破均線 / 長黑跌破均線: a large bullish/bearish candle that closes through the
    MA<period>. `direction` up = 長紅 (spread/prev_close ≥ min_body_pct AND today closes
    above the MA while the prior bar was below); down = 長黑 (mirror)."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    if direction == "up":
        body_cond = "(last_spread / NULLIF(last_close - last_spread, 0)) * 100 >= ?"
        cross_cond = "last_adj > ma_today AND prev_adj <= ma_prev"
    else:
        body_cond = "(last_spread / NULLIF(last_close - last_spread, 0)) * 100 <= ?"
        cross_cond = "last_adj < ma_today AND prev_adj >= ma_prev"
    sign_thresh = min_body_pct if direction == "up" else -min_body_pct
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS ma_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS ma_prev,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 2 THEN adj_close END) AS prev_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1 AND (last_close - last_spread) > 0
          AND {body_cond}
          AND {cross_cond}
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [period, period, period, sign_thresh, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_ma_above_rising(self: "MarketDataCache", period: int = 20, limit: int = 30) -> list[dict[str, Any]]:
    """股價在月線上 & 月線上揚: last close above MA<period> AND the MA is rising
    (today's MA > yesterday's). The bullish-stack screen from the image."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(CASE WHEN rn <= ? THEN adj_close END) AS ma_today,
                   AVG(CASE WHEN rn BETWEEN 2 AND ? + 1 THEN adj_close END) AS ma_prev,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= ? + 1 AND last_adj > ma_today AND ma_today > ma_prev
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [period, period, period, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_bollinger_breakout(self: "MarketDataCache", limit: int = 30) -> list[dict[str, Any]]:
    """Last close above the upper Bollinger band (20-period, 2σ)."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   AVG(adj_close) AS ma,
                   STDDEV_POP(adj_close) AS sd,
                   MAX(CASE WHEN rn = 1 THEN adj_close END) AS last_adj,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   COUNT(*) AS n
            FROM recent
            WHERE rn <= 20
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= 20 AND sd > 0 AND last_adj > ma + 2 * sd
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_surge(
    self: "MarketDataCache", min_change_pct: float = 7.0, limit: int = 30
) -> list[dict[str, Any]]:
    """Single-day move (|spread / prev close|) greater than threshold, on the latest bar."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        SELECT stock_id, close, spread, volume,
               ROUND(ABS(spread) / NULLIF(close - spread, 0) * 100, 2) AS chg
        FROM price_daily
        WHERE {TW_ID_FILTER} AND date = ? AND close > 0
          AND (close - spread) > 0
          AND ABS(spread) / (close - spread) * 100 > ?
        ORDER BY chg DESC
        LIMIT ?
        """,
        [as_of, min_change_pct, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_volume_spike(
    self: "MarketDataCache", mult: float = 3.0, limit: int = 30
) -> list[dict[str, Any]]:
    """Latest volume greater than `mult` × the trailing 20-bar average volume."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        WITH recent AS (
            SELECT stock_id, close, spread, volume,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM price_daily
            WHERE {TW_ID_FILTER} AND volume > 0
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS today_vol,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   AVG(CASE WHEN rn BETWEEN 2 AND 21 THEN volume END) AS avg_vol,
                   COUNT(*) AS n
            FROM recent
            WHERE rn <= 21
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, today_vol,
               ROUND(today_vol / NULLIF(avg_vol, 0), 1) AS vol_ratio
        FROM agg
        WHERE n >= 6 AND avg_vol > 0 AND today_vol > avg_vol * ?
        ORDER BY vol_ratio DESC
        LIMIT ?
        """,
        [mult, limit],
    )
    return [
        {"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3], "vol_ratio": r[4]}
        for r in rows
    ]


async def screen_price_breakout(
    self: "MarketDataCache", lookback: int = 250, limit: int = 30
) -> list[dict[str, Any]]:
    """Latest high exceeds the prior `lookback`-bar high (52-week breakout)."""
    as_of = await self._latest_price_date()
    if not as_of:
        return []
    rows = await self._engine.aquery(
        f"""
        {ADJ_PRICE_CTE},
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN adj_high END) AS today_high,
                   MAX(CASE WHEN rn = 1 THEN close END) AS last_close,
                   MAX(CASE WHEN rn = 1 THEN spread END) AS last_spread,
                   MAX(CASE WHEN rn = 1 THEN volume END) AS last_volume,
                   MAX(CASE WHEN rn BETWEEN 2 AND ? THEN adj_high END) AS prior_high,
                   COUNT(*) AS n
            FROM recent
            WHERE rn <= ?
            GROUP BY stock_id
        )
        SELECT stock_id, last_close, last_spread, last_volume
        FROM agg
        WHERE n >= 20 AND prior_high > 0 AND today_high > prior_high
        ORDER BY last_volume DESC
        LIMIT ?
        """,
        [lookback, lookback, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_kd_cross(self: "MarketDataCache", direction: str, limit: int = 30) -> list[dict[str, Any]]:
    """日KD 向上交叉 / 向下交叉: the daily K line crosses the D line. `direction` up =
    golden (K was ≤ D yesterday, > D today); down = death. Reads the precomputed
    indicators_daily (kd_k/kd_d + their prev values). Joins price_daily for the latest
    close/spread/volume to render a rich row."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM indicators_daily", None)
    if not guard or not guard[0]:
        return []
    today_cmp, prev_cmp = (">", "<=") if direction == "up" else ("<", ">=")
    rows = await self._engine.aquery(
        f"""
        WITH px AS (
            SELECT stock_id, close, spread, volume,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM price_daily
            WHERE {TW_ID_FILTER} AND close > 0
        )
        SELECT i.stock_id, px.close, px.spread, px.volume
        FROM indicators_daily i
        JOIN px ON px.stock_id = i.stock_id AND px.rn = 1
        WHERE i.kd_k IS NOT NULL AND i.kd_d IS NOT NULL
          AND i.kd_k_prev IS NOT NULL AND i.kd_d_prev IS NOT NULL
          AND i.kd_k {today_cmp} i.kd_d
          AND i.kd_k_prev {prev_cmp} i.kd_d_prev
        ORDER BY px.volume DESC
        LIMIT ?
        """,
        [limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]


async def screen_macd_flip(self: "MarketDataCache", direction: str, limit: int = 30) -> list[dict[str, Any]]:
    """日MACD柱狀體 負轉正 / 轉負: the MACD histogram flips sign. `direction` up = 負轉正
    (hist was ≤ 0 yesterday, > 0 today); down = 轉負 (mirror). Reads indicators_daily."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM indicators_daily", None)
    if not guard or not guard[0]:
        return []
    today_cmp, prev_cmp = ("> 0", "<= 0") if direction == "up" else ("< 0", ">= 0")
    rows = await self._engine.aquery(
        f"""
        WITH px AS (
            SELECT stock_id, close, spread, volume,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM price_daily
            WHERE {TW_ID_FILTER} AND close > 0
        )
        SELECT i.stock_id, px.close, px.spread, px.volume
        FROM indicators_daily i
        JOIN px ON px.stock_id = i.stock_id AND px.rn = 1
        WHERE i.macd_hist IS NOT NULL AND i.macd_hist_prev IS NOT NULL
          AND i.macd_hist {today_cmp}
          AND i.macd_hist_prev {prev_cmp}
        ORDER BY px.volume DESC
        LIMIT ?
        """,
        [limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": r[1], "spread": r[2], "volume": r[3]} for r in rows]
