"""MarketDataCache — latest-session resolution and quote enrichment.

Bound onto MarketDataCache in __init__.py. Behavior identical to the original
monolithic market_cache.py.
"""

from typing import TYPE_CHECKING, Any, cast

from app.db.duckdb.market_cache._sql import LATEST_COMPLETE_DATE_SQL

if TYPE_CHECKING:
    from datetime import date

    from app.db.duckdb.market_cache import MarketDataCache


async def _latest_price_date(self: "MarketDataCache") -> Any:
    row = await self._engine.aquery_one(LATEST_COMPLETE_DATE_SQL, None)
    if row and row[0]:
        return row[0]
    # Fallback: nothing crossed the completeness bar yet → use the absolute max.
    row = await self._engine.aquery_one("SELECT MAX(date) FROM price_daily", None)
    return row[0] if row else None


async def latest_price_date(self: "MarketDataCache") -> "date | None":
    """Public accessor: the most recent COMPLETE trading date stored in price_daily."""
    return cast("date | None", await self._latest_price_date())


async def enrich_quotes(
    self: "MarketDataCache", stock_ids: list[str], spark_days: int = 20
) -> dict[str, dict[str, Any]]:
    """Latest OHLC bar + a recent close sparkline for each stock_id.

    Used to decorate screener results (and any stock list) with the data the UI
    needs for rich rows: a single candlestick (open/high/low/close), the latest
    close / change / volume, and a short close series for a mini-kline. Reads the
    columnar store in two scans regardless of how many ids are requested — no
    per-stock HTTP. Returns {} for ids with no stored history.
    """
    if not stock_ids:
        return {}
    ids = sorted(set(stock_ids))
    placeholders = ", ".join(["?"] * len(ids))

    # Latest complete bar per stock.
    latest = await self._engine.aquery(
        f"""
        WITH recent AS (
            SELECT stock_id, open, high, low, close, spread, volume,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM price_daily
            WHERE stock_id IN ({placeholders}) AND close > 0
              AND date <= ({LATEST_COMPLETE_DATE_SQL.strip()})
        )
        SELECT stock_id, open, high, low, close, spread, volume
        FROM recent WHERE rn = 1
        """,
        ids,
    )
    out: dict[str, dict[str, Any]] = {}
    for r in latest:
        out[r[0]] = {
            "open": r[1], "high": r[2], "low": r[3], "close": r[4],
            "spread": r[5], "volume": r[6], "spark": [],
        }

    # Recent close series (oldest→newest) for the mini-kline.
    sparks = await self._engine.aquery(
        f"""
        WITH recent AS (
            SELECT stock_id, date, close,
                   ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
            FROM price_daily
            WHERE stock_id IN ({placeholders}) AND close > 0
              AND date <= ({LATEST_COMPLETE_DATE_SQL.strip()})
        )
        SELECT stock_id, close
        FROM recent WHERE rn <= ?
        ORDER BY stock_id, date
        """,
        [*ids, spark_days],
    )
    for sid, close in sparks:
        if sid in out:
            out[sid]["spark"].append(close)
    return out
