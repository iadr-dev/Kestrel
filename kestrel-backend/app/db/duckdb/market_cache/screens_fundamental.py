"""MarketDataCache — fundamental screens (revenue / EPS / margin).

Scan revenue_monthly + financials_quarterly with SQL window functions. These tables
carry no price, so rows return close/spread/volume = 0 and the screener's
_enrich_with_quotes backfills the latest bar (same pattern as the chip screens).
Bound onto MarketDataCache in __init__.py.
"""

from typing import TYPE_CHECKING, Any

from app.db.duckdb.market_cache._sql import TW_ID_FILTER

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache

_EMPTY_PRICE = {"close": 0, "spread": 0, "volume": 0}


def _rows(result: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [{"stock_id": r[0], "stock_name": "", **_EMPTY_PRICE} for r in result]


async def screen_rev_yoy_streak(
    self: "MarketDataCache", direction: str, months: int = 3, threshold: float = 20.0, limit: int = 30
) -> list[dict[str, Any]]:
    """連N月營收年增 / 年減 > X%: the latest `months` monthly revenue YoY readings are ALL
    above +threshold (up) / below −threshold (down). revenue_yoy is computed at ingest."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM revenue_monthly", None)
    if not guard or not guard[0]:
        return []
    cond = "revenue_yoy > ?" if direction == "up" else "revenue_yoy < ?"
    thr = threshold if direction == "up" else -threshold
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, revenue_yoy,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM revenue_monthly
            WHERE {TW_ID_FILTER}
        )
        SELECT stock_id, COUNT(*) AS cnt
        FROM ranked
        WHERE rn <= ? AND {cond}
        GROUP BY stock_id
        HAVING COUNT(*) >= ?
        ORDER BY stock_id
        LIMIT ?
        """,
        [months, thr, months, limit],
    )
    return _rows(result)


async def screen_rev_month_extreme(
    self: "MarketDataCache", direction: str, min_months: int = 12, limit: int = 30
) -> list[dict[str, Any]]:
    """月營收創新高 / 新低: the latest month's revenue is the max / min over all stored
    months (≥ min_months of history). 'New high/low' relative to the stored window."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM revenue_monthly", None)
    if not guard or not guard[0]:
        return []
    pick = "latest_rev >= max_rev" if direction == "high" else "latest_rev <= min_rev"
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, revenue,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM revenue_monthly
            WHERE {TW_ID_FILTER} AND revenue > 0
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN revenue END) AS latest_rev,
                   MAX(revenue) AS max_rev,
                   MIN(revenue) AS min_rev,
                   COUNT(*) AS n
            FROM ranked
            GROUP BY stock_id
        )
        SELECT stock_id
        FROM agg
        WHERE n >= ? AND latest_rev IS NOT NULL AND {pick}
        ORDER BY stock_id
        LIMIT ?
        """,
        [min_months, limit],
    )
    return _rows(result)


async def screen_eps_extreme(
    self: "MarketDataCache", direction: str, min_quarters: int = 5, limit: int = 30
) -> list[dict[str, Any]]:
    """近一季EPS創新高 / 新低: latest quarter EPS is the max / min over stored quarters."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []
    pick = "latest_eps >= max_eps" if direction == "high" else "latest_eps <= min_eps"
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, eps,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly
            WHERE {TW_ID_FILTER}
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN eps END) AS latest_eps,
                   MAX(eps) AS max_eps,
                   MIN(eps) AS min_eps,
                   COUNT(*) AS n
            FROM ranked
            GROUP BY stock_id
        )
        SELECT stock_id
        FROM agg
        WHERE n >= ? AND latest_eps IS NOT NULL AND {pick}
        ORDER BY stock_id
        LIMIT ?
        """,
        [min_quarters, limit],
    )
    return _rows(result)


async def screen_eps_yoy(
    self: "MarketDataCache", direction: str, threshold: float = 10.0, limit: int = 30
) -> list[dict[str, Any]]:
    """近一季EPS年增 / 年減 > X%: latest quarter EPS vs the SAME quarter last year (4
    quarters back = rn 5). direction up → growth > +threshold; down → < −threshold."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []
    cmp = "> ?" if direction == "up" else "< ?"
    thr = threshold if direction == "up" else -threshold
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, eps,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly
            WHERE {TW_ID_FILTER}
        ),
        agg AS (
            SELECT stock_id,
                   MAX(CASE WHEN rn = 1 THEN eps END) AS eps_now,
                   MAX(CASE WHEN rn = 5 THEN eps END) AS eps_base,
                   COUNT(*) AS n
            FROM ranked
            WHERE rn <= 5
            GROUP BY stock_id
        )
        SELECT stock_id
        FROM agg
        WHERE n >= 5 AND eps_base IS NOT NULL AND eps_base <> 0
          AND (eps_now - eps_base) / ABS(eps_base) * 100 {cmp}
        ORDER BY stock_id
        LIMIT ?
        """,
        [thr, limit],
    )
    return _rows(result)


# Which financials_quarterly column each margin metric maps to.
_MARGIN_COL = {"gross": "gross_margin", "operating": "operating_margin", "net": "net_margin"}


async def screen_margin_threshold(
    self: "MarketDataCache", metric: str, threshold: float = 30.0, quarters: int = 4, required: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """近四季有三季 毛利率>X% / 營益率>X%: at least `required` of the last `quarters`
    quarters have the margin above threshold. metric ∈ {gross, operating, net}."""
    col = _MARGIN_COL.get(metric)
    if col is None:
        return []
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, {col} AS m,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly
            WHERE {TW_ID_FILTER}
        )
        SELECT stock_id, COUNT(*) AS cnt
        FROM ranked
        WHERE rn <= ? AND m > ?
        GROUP BY stock_id
        HAVING COUNT(*) >= ?
        ORDER BY stock_id
        LIMIT ?
        """,
        [quarters, threshold, required, limit],
    )
    return _rows(result)


async def screen_margin_decline(
    self: "MarketDataCache", metric: str, quarters: int = 4, limit: int = 30
) -> list[dict[str, Any]]:
    """毛利率連N季衰退: the margin strictly declined across the last `quarters` quarters
    (each newer quarter lower than the older one). metric ∈ {gross, operating, net}."""
    col = _MARGIN_COL.get(metric)
    if col is None:
        return []
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []
    # Build the strict-decline chain m[rn=1] < m[rn=2] < ... < m[rn=quarters].
    picks = ", ".join(f"MAX(CASE WHEN rn = {i} THEN {col} END) AS m{i}" for i in range(1, quarters + 1))
    chain = " AND ".join(f"m{i} < m{i + 1}" for i in range(1, quarters))
    nonnull = " AND ".join(f"m{i} IS NOT NULL" for i in range(1, quarters + 1))
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, {col},
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly
            WHERE {TW_ID_FILTER}
        ),
        agg AS (
            SELECT stock_id, {picks}, COUNT(*) AS n
            FROM ranked WHERE rn <= {quarters}
            GROUP BY stock_id
        )
        SELECT stock_id
        FROM agg
        WHERE n >= {quarters} AND {nonnull} AND {chain}
        ORDER BY stock_id
        LIMIT ?
        """,
        [limit],
    )
    return _rows(result)


async def screen_dividend_yield(
    self: "MarketDataCache", threshold: float = 5.0, limit: int = 30
) -> list[dict[str, Any]]:
    """現金殖利率 > X%: latest per_daily dividend_yield above threshold."""
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM per_daily", None)
    if not guard or not guard[0]:
        return []
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, dividend_yield,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM per_daily WHERE {TW_ID_FILTER}
        )
        SELECT stock_id FROM ranked
        WHERE rn = 1 AND dividend_yield > ?
        ORDER BY dividend_yield DESC
        LIMIT ?
        """,
        [threshold, limit],
    )
    return _rows(result)


_RATIO_COL = {"debt": "debt_ratio", "quick": "quick_ratio"}


async def screen_ttm_return(
    self: "MarketDataCache", metric: str, threshold: float, windows: int = 1, limit: int = 30
) -> list[dict[str, Any]]:
    """TTM ROE / ROA > X%. A single quarter's ROE (≈5%) isn't the ~20% ANNUAL figure
    screeners mean, so we sum each rolling 4-quarter net income over the window-start
    equity (ROE) / total assets (ROA). `windows` = how many consecutive trailing-year
    windows must clear the threshold (1 = latest TTM; 連續N年ROE>X ⇒ windows=N, each
    window stepping back 4 quarters). metric ∈ {roe, roa}."""
    if metric not in ("roe", "roa"):
        return []
    denom = "equity" if metric == "roe" else "total_assets"
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []

    need = windows + 3  # each of `windows` TTM windows needs a full trailing 4 quarters
    pivots = ", ".join(
        f"MAX(CASE WHEN rn = {i} THEN net_income END) AS ni{i}, "
        f"MAX(CASE WHEN rn = {i} THEN {denom} END) AS den{i}"
        for i in range(1, need + 1)
    )
    # For window `off` (0-based): TTM = ni[off+1..off+4] summed, over den[off+1].
    checks = []
    params: list[Any] = []
    for off in range(windows):
        ni_sum = " + ".join(f"ni{off + j}" for j in range(1, 5))
        checks.append(f"(({ni_sum}) / NULLIF(den{off + 1}, 0) * 100) > ?")
        params.append(threshold)
    where_all = " AND ".join(checks)

    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, net_income, {denom},
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly WHERE {TW_ID_FILTER}
        ),
        agg AS (
            SELECT stock_id, COUNT(*) AS n, {pivots}
            FROM ranked WHERE rn <= {need}
            GROUP BY stock_id
        )
        SELECT stock_id FROM agg
        WHERE n >= {need} AND {where_all}
        ORDER BY stock_id
        LIMIT ?
        """,
        [*params, limit],
    )
    return _rows(result)


async def screen_ratio(
    self: "MarketDataCache", metric: str, op: str, threshold: float, quarters: int = 4, required: int = 3, limit: int = 30
) -> list[dict[str, Any]]:
    """Snapshot balance-sheet ratio: 負債比 / 速動比 over the last `quarters` quarters,
    requiring `required` to satisfy `op` threshold. metric ∈ {debt, quick}; op ∈ {gt,lt}.
    (ROE/ROA use screen_ttm_return — single-quarter ratios understate the annual figure.)"""
    col = _RATIO_COL.get(metric)
    if col is None or op not in ("gt", "lt"):
        return []
    guard = await self._engine.aquery_one("SELECT MAX(date) FROM financials_quarterly", None)
    if not guard or not guard[0]:
        return []
    cmp = ">" if op == "gt" else "<"
    result = await self._engine.aquery(
        f"""
        WITH ranked AS (
            SELECT stock_id, {col} AS v,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM financials_quarterly WHERE {TW_ID_FILTER}
        )
        SELECT stock_id, COUNT(*) AS cnt
        FROM ranked
        WHERE rn <= ? AND v IS NOT NULL AND v {cmp} ?
        GROUP BY stock_id
        HAVING COUNT(*) >= ?
        ORDER BY stock_id
        LIMIT ?
        """,
        [quarters, threshold, required, limit],
    )
    return _rows(result)
