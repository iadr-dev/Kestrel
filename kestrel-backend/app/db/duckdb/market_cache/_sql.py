"""Shared SQL fragments and constants for the MarketDataCache screen modules.

Kept in one place so the screener CTEs (price + chip) embed identical definitions
of "latest complete session", the TW-ID filter, and the back-adjusted price CTE.
"""

# Latest COMPLETE trading session in price_daily. A finished session has the whole
# market (~40k rows); an in-progress intraday/boot ingest can leave a partial day
# (e.g. 2 rows) as MAX(date). Screens that anchor on the latest bar must ignore such
# partial days, so "latest" everywhere = the most recent date whose row count is at
# least half the busiest day.
LATEST_COMPLETE_DATE_SQL = """
    SELECT MAX(date) FROM (
        SELECT date, COUNT(*) AS n FROM price_daily GROUP BY date
    ) d
    WHERE n >= 0.5 * (SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM price_daily GROUP BY date))
"""

# Restrict screens to 4-digit numeric TW common-stock IDs.
TW_ID_FILTER = "stock_id SIMILAR TO '[0-9]{4}'"

# FinMind institution codes per investor group (stored in institutional_daily.institution).
INVESTOR_CODES: dict[str, tuple[str, ...]] = {
    "foreign": ("Foreign_Investor", "Foreign_Dealer_Self"),  # 外資
    "trust": ("Investment_Trust",),                          # 投信
    "dealer": ("Dealer_self", "Dealer_Hedging"),             # 自營商
    # "all" → no filter (三大法人)
}

# Back-adjusted price CTE (split / ex-rights / ex-dividend continuity).
#
# Taiwan equities have a ±10% daily price limit, so ANY close-to-close move
# outside a conservative band is provably an adjustment boundary (split / rights
# / large dividend), not a real trade — e.g. raw 1589 jumps 5.54→80.6 (×14.5),
# which would make a 5-day "return" read +1012%. Multi-day analytics (returns,
# MAs, Bollinger, breakout) must run on a CONTINUOUS series, matching the
# Yahoo/CRSP adjusted-close standard.
#
# We derive the adjustment factor from the series itself (no split feed, no extra
# API calls): at each boundary the ratio is close/prev_close; a row's back-factor
# is the cumulative product of every ratio that occurs AFTER it (suffix product
# via EXP(SUM(LN(ratio))) over the following rows). adj_close = close * back_factor
# leaves the latest bar untouched and scales history onto today's basis.
#
# Band: >25% up or <−20% down. Two stacked ±10% limit days max ≈ ±21%, so this
# never misfires on real limit moves while still catching every real adjustment.
ADJ_PRICE_CTE = f"""
    WITH _ratios AS (
        SELECT stock_id, date, close, spread, volume, high,
               CASE WHEN LAG(close) OVER w > 0
                         AND (close / LAG(close) OVER w > 1.25
                              OR close / LAG(close) OVER w < 0.80)
                    THEN close / LAG(close) OVER w ELSE 1.0 END AS adj_ratio
        FROM price_daily
        WHERE {TW_ID_FILTER} AND close > 0
          -- ignore an in-progress partial day so `rn = 1` is a real session
          AND date <= ({LATEST_COMPLETE_DATE_SQL.strip()})
        WINDOW w AS (PARTITION BY stock_id ORDER BY date)
    ),
    adj AS (
        SELECT stock_id, date, spread, volume, close, high,
               COALESCE(
                   EXP(SUM(LN(adj_ratio)) OVER (
                       PARTITION BY stock_id ORDER BY date
                       ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING
                   )), 1.0
               ) AS back_factor
        FROM _ratios
    ),
    recent AS (
        SELECT stock_id, date, close, spread, volume, high,
               close * back_factor AS adj_close,
               high * back_factor AS adj_high,
               ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
        FROM adj
    )
"""
