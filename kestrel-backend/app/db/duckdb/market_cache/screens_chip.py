"""MarketDataCache — chip/flow screens (institutional buy/sell, margin).

Scan institutional_daily / margin_daily with SQL window functions. Bound onto
MarketDataCache in __init__.py.
"""

from typing import TYPE_CHECKING, Any

from app.db.duckdb.market_cache._sql import INVESTOR_CODES, TW_ID_FILTER

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache


async def screen_institutional_streak(
    self: "MarketDataCache", min_streak: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """Stocks with institutional net-buy on each of the last `min_streak` trading days."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM institutional_daily", None)
    if not guard or not guard[0]:
        return []
    result = await self._engine.aquery(
        f"""
        WITH daily AS (
            SELECT stock_id, date, SUM(buy - sell) AS net
            FROM institutional_daily
            WHERE {TW_ID_FILTER}
            GROUP BY stock_id, date
        ),
        ranked AS (
            SELECT stock_id, date, net,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM daily
        )
        SELECT stock_id, COUNT(*) AS streak
        FROM ranked
        WHERE rn <= ? AND net > 0
        GROUP BY stock_id
        HAVING COUNT(*) >= ?
        ORDER BY streak DESC
        LIMIT ?
        """,
        [min_streak, min_streak, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0, "streak": r[1]} for r in result]


async def screen_institutional_streak_by(
    self: "MarketDataCache", investor: str, direction: str, min_streak: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """連N買 / 連N賣 for a specific investor group. `investor` ∈ {all,foreign,trust,
    dealer}; `direction` ∈ {buy,sell}. A stock qualifies when the chosen group's
    daily net (buy−sell) was strictly positive (buy) / negative (sell) on each of
    the last `min_streak` trading days. Mirrors screen_institutional_streak but
    scoped by investor + direction."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM institutional_daily", None)
    if not guard or not guard[0]:
        return []

    codes = INVESTOR_CODES.get(investor)
    where_inv = ""
    params: list[Any] = []
    if codes:
        where_inv = f"AND institution IN ({','.join('?' * len(codes))})"
        params.extend(codes)
    net_cond = "net > 0" if direction == "buy" else "net < 0"
    params.extend([min_streak, min_streak, limit])

    result = await self._engine.aquery(
        f"""
        WITH daily AS (
            SELECT stock_id, date, SUM(buy - sell) AS net
            FROM institutional_daily
            WHERE {TW_ID_FILTER} {where_inv}
            GROUP BY stock_id, date
        ),
        ranked AS (
            SELECT stock_id, date, net,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM daily
        )
        SELECT stock_id, COUNT(*) AS streak
        FROM ranked
        WHERE rn <= ? AND {net_cond}
        GROUP BY stock_id
        HAVING COUNT(*) >= ?
        ORDER BY streak DESC
        LIMIT ?
        """,
        params,
    )
    return [{"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0, "streak": r[1]} for r in result]


async def screen_institutional_net_ndays(
    self: "MarketDataCache", investor: str, direction: str, days: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """近N日買超 / 賣超 for a specific investor group — ranks stocks by the chosen
    group's summed net (buy−sell) over the last `days` trading days. `direction`
    buy → largest positive sum first; sell → largest negative sum first."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM institutional_daily", None)
    if not guard or not guard[0]:
        return []

    codes = INVESTOR_CODES.get(investor)
    where_inv = ""
    params: list[Any] = []
    if codes:
        where_inv = f"AND institution IN ({','.join('?' * len(codes))})"
        params.extend(codes)
    order = "net_sum DESC" if direction == "buy" else "net_sum ASC"
    having = "net_sum > 0" if direction == "buy" else "net_sum < 0"
    params.extend([days, limit])

    result = await self._engine.aquery(
        f"""
        WITH daily AS (
            SELECT stock_id, date, SUM(buy - sell) AS net
            FROM institutional_daily
            WHERE {TW_ID_FILTER} {where_inv}
            GROUP BY stock_id, date
        ),
        ranked AS (
            SELECT stock_id, net,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM daily
        )
        SELECT stock_id, SUM(net) AS net_sum
        FROM ranked
        WHERE rn <= ?
        GROUP BY stock_id
        HAVING {having}
        ORDER BY {order}
        LIMIT ?
        """,
        params,
    )
    return [{"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0, "net": r[1]} for r in result]


async def screen_institutional_buy(self: "MarketDataCache", limit: int = 30) -> list[dict[str, Any]]:
    """Largest institutional net-buy on the latest available day."""
    row = await self._engine.aquery_one("SELECT MAX(date) FROM institutional_daily", None)
    as_of = row[0] if row else None
    if not as_of:
        return []
    result = await self._engine.aquery(
        f"""
        SELECT stock_id, SUM(buy - sell) AS net
        FROM institutional_daily
        WHERE {TW_ID_FILTER} AND date = ?
        GROUP BY stock_id
        HAVING SUM(buy - sell) > 0
        ORDER BY net DESC
        LIMIT ?
        """,
        [as_of, limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0, "net": r[1]} for r in result]


async def screen_foreign_holding_change(
    self: "MarketDataCache", direction: str, days: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """外資持股率增加 / 減少 — rank stocks by the change in foreign holding % over the
    last `days` trading days (latest foreign_ratio minus the ratio `days` sessions
    ago). `direction` buy → largest increase first; sell → largest decrease first.
    Source: shareholding_daily (TaiwanStockShareholding, 外資持股比例)."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM shareholding_daily", None)
    if not guard or not guard[0]:
        return []

    order = "delta DESC" if direction == "buy" else "delta ASC"
    having = "delta > 0" if direction == "buy" else "delta < 0"

    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, date, foreign_ratio,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM shareholding_daily
            WHERE {TW_ID_FILTER} AND foreign_ratio IS NOT NULL
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN foreign_ratio END) AS now_ratio,
                   MAX(CASE WHEN rn = ? + 1 THEN foreign_ratio END) AS then_ratio,
                   COUNT(*) AS n
            FROM ranked
            WHERE rn <= ? + 1
            GROUP BY stock_id
        )
        SELECT stock_id, now_ratio, ROUND(now_ratio - then_ratio, 2) AS delta
        FROM agg
        WHERE n >= ? + 1 AND then_ratio IS NOT NULL AND {having}
        ORDER BY {order}
        LIMIT ?
        """,
        [days, days, days, limit],
    )
    return [
        {"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0,
         "foreign_ratio": r[1], "ratio_delta": r[2]}
        for r in result
    ]


async def screen_margin_squeeze(self: "MarketDataCache", limit: int = 30) -> list[dict[str, Any]]:
    """Margin (融資) balance falling while short (融券) balance rising over recent bars."""
    row = await self._engine.aquery_one("SELECT MAX(date) FROM margin_daily", None)
    as_of = row[0] if row else None
    if not as_of:
        return []
    result = await self._engine.aquery(
        f"""
        WITH recent AS (
            SELECT stock_id, date, margin_balance, short_balance,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM margin_daily
            WHERE {TW_ID_FILTER}
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN margin_balance END) AS m_now,
                   MAX(CASE WHEN rn = 5 THEN margin_balance END) AS m_then,
                   MAX(CASE WHEN rn = 1 THEN short_balance END) AS s_now,
                   MAX(CASE WHEN rn = 5 THEN short_balance END) AS s_then,
                   COUNT(*) AS n
            FROM recent
            WHERE rn <= 5
            GROUP BY stock_id
        )
        SELECT stock_id
        FROM agg
        WHERE n >= 5 AND m_now < m_then AND s_now > s_then
        LIMIT ?
        """,
        [limit],
    )
    return [{"stock_id": r[0], "stock_name": "", "close": 0, "spread": 0, "volume": 0} for r in result]
