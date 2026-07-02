"""MarketDataCache — storage & raw reads (price / institutional / generic JSON).

Methods are defined as free functions taking `self` and bound onto MarketDataCache
in __init__.py (same composition pattern as YFinanceProvider). Behavior is identical
to the original monolithic market_cache.py.
"""

import asyncio
import json
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache

_PRICE_COLUMNS = ["stock_id", "date", "open", "high", "low", "close", "volume", "amount", "spread", "turnover"]
_VALID_TABLES = {"price_daily", "institutional_daily", "revenue_monthly", "stock_scores", "ai_summaries"}


async def get_price_data(
    self: "MarketDataCache", stock_id: str, start_date: date, end_date: date | None = None
) -> list[dict[str, Any]] | None:
    """Read cached price data. Returns None on cache miss.

    Async: uses the engine's aquery so it runs off the event loop (acquiring
    the read lock in a worker thread) instead of blocking it with a sync
    cursor — important under high concurrency.
    """
    query = """
        SELECT stock_id, date, open, high, low, close, volume, amount, spread, turnover
        FROM price_daily
        WHERE stock_id = ? AND date >= ?
    """
    params: list[Any] = [stock_id, start_date]
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date"

    result = await self._engine.aquery(query, params)
    if not result:
        return None
    return [dict(zip(_PRICE_COLUMNS, row, strict=False)) for row in result]


async def store_price_data(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    """Batch upsert price data. Returns number of rows written.

    Async wrapper offloads the (locking) write to a worker thread so it never
    blocks the event loop.
    """
    return await asyncio.to_thread(_store_price_data_sync, self, records)


def _store_price_data_sync(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    if not records:
        return 0

    with self._engine.write_connection() as conn:
        rows = [
            (
                r.get("stock_id"),
                r.get("date"),
                r.get("open"),
                r.get("max", r.get("high")),
                r.get("min", r.get("low")),
                r.get("close"),
                r.get("Trading_Volume", r.get("volume")),
                r.get("Trading_money", r.get("amount")),
                r.get("spread"),
                r.get("Trading_turnover", r.get("turnover")),
            )
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO price_daily
               (stock_id, date, open, high, low, close, volume, amount, spread, turnover)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        return len(rows)


async def get_institutional_data(
    self: "MarketDataCache", stock_id: str, start_date: date, end_date: date | None = None
) -> list[dict[str, Any]] | None:
    query = """
        SELECT stock_id, date, institution, buy, sell
        FROM institutional_daily
        WHERE stock_id = ? AND date >= ?
    """
    params: list[Any] = [stock_id, start_date]
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date, institution"

    result = await self._engine.aquery(query, params)
    if not result:
        return None
    columns = ["stock_id", "date", "institution", "buy", "sell"]
    return [dict(zip(columns, row, strict=False)) for row in result]


async def store_institutional_data(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    return await asyncio.to_thread(_store_institutional_data_sync, self, records)


def _store_institutional_data_sync(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    with self._engine.write_connection() as conn:
        rows = [
            (
                r.get("stock_id"),
                r.get("date"),
                r.get("name", r.get("institution")),
                r.get("buy"),
                r.get("sell"),
            )
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO institutional_daily
               (stock_id, date, institution, buy, sell)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )
        return len(rows)


async def get_generic_cache(
    self: "MarketDataCache", dataset: str, stock_id: str | None, start_date: date, end_date: date | None = None
) -> list[dict[str, Any]] | None:
    """Generic JSON cache for arbitrary datasets."""
    query = "SELECT data FROM market_cache WHERE dataset = ? AND date >= ?"
    params: list[Any] = [dataset, start_date]
    if stock_id:
        query += " AND stock_id = ?"
        params.append(stock_id)
    else:
        query += " AND stock_id IS NULL"
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date"

    result = await self._engine.aquery(query, params)
    if not result:
        return None
    return [json.loads(row[0]) for row in result]


async def store_generic_cache(
    self: "MarketDataCache", dataset: str, stock_id: str | None, records: list[dict[str, Any]]
) -> int:
    return await asyncio.to_thread(_store_generic_cache_sync, self, dataset, stock_id, records)


def _store_generic_cache_sync(
    self: "MarketDataCache", dataset: str, stock_id: str | None, records: list[dict[str, Any]]
) -> int:
    if not records:
        return 0
    with self._engine.write_connection() as conn:
        rows = [
            (dataset, stock_id, r.get("date"), json.dumps(r))
            for r in records
            if r.get("date")
        ]
        if rows:
            conn.executemany(
                """INSERT OR REPLACE INTO market_cache (dataset, stock_id, date, data)
                   VALUES (?, ?, ?, ?)""",
                rows,
            )
        return len(rows)


async def store_shareholding_data(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    """Batch upsert foreign-shareholding rows into shareholding_daily."""
    return await asyncio.to_thread(_store_shareholding_data_sync, self, records)


def _store_shareholding_data_sync(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    with self._engine.write_connection() as conn:
        rows = [
            (
                r.get("stock_id"),
                r.get("date"),
                r.get("ForeignInvestmentShares", r.get("foreign_shares")),
                r.get("ForeignInvestmentSharesRatio", r.get("foreign_ratio")),
                r.get("NumberOfSharesIssued", r.get("issued_shares")),
            )
            for r in records
        ]
        conn.executemany(
            """INSERT OR REPLACE INTO shareholding_daily
               (stock_id, date, foreign_shares, foreign_ratio, issued_shares)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )
        return len(rows)


async def store_etf_nav_data(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    """Batch upsert daily ETF NAV / market price / premium-discount snapshots.

    Accepts rows shaped like the NAV scraper output (estimated_nav / market_price /
    premium_discount_pct as strings) and coerces the numeric fields; one row per
    (etf_id, date) so re-running the same day overwrites rather than duplicates.
    """
    return await asyncio.to_thread(_store_etf_nav_data_sync, self, records)


def _store_etf_nav_data_sync(self: "MarketDataCache", records: list[dict[str, Any]]) -> int:
    if not records:
        return 0

    def _num(v: Any) -> float | None:
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None

    with self._engine.write_connection() as conn:
        rows = [
            (
                r.get("etf_id"),
                r.get("date"),
                _num(r.get("market_price")),
                _num(r.get("estimated_nav", r.get("nav"))),
                _num(r.get("premium_discount_pct")),
            )
            for r in records
            if r.get("etf_id") and r.get("date")
        ]
        if rows:
            conn.executemany(
                """INSERT OR REPLACE INTO etf_nav_daily
                   (etf_id, date, market_price, nav, premium_discount_pct)
                   VALUES (?, ?, ?, ?, ?)""",
                rows,
            )
        return len(rows)


async def get_etf_nav_history(
    self: "MarketDataCache", etf_id: str, start_date: date, end_date: date | None = None
) -> list[dict[str, Any]]:
    """Read persisted daily NAV / premium-discount history for one ETF (oldest first)."""
    query = """
        SELECT etf_id, date, market_price, nav, premium_discount_pct
        FROM etf_nav_daily
        WHERE etf_id = ? AND date >= ?
    """
    params: list[Any] = [etf_id, start_date]
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date"

    result = await self._engine.aquery(query, params)
    columns = ["etf_id", "date", "market_price", "nav", "premium_discount_pct"]
    return [dict(zip(columns, row, strict=False)) for row in result]


async def get_etf_holdings_ops(self: "MarketDataCache", etf_id: str) -> dict[str, Any]:
    """Diff an active ETF's two most recent holdings snapshots into an operations log.

    Returns {"latest": <date>, "prior": <date>, "ops": [{stock_name, action, ...}]}.
    action ∈ 新增/刪除/加碼/減碼. Empty ops (and prior=None) until ≥2 snapshot days
    exist. Δ張數 and Δ權重 come from the latest vs prior rows."""
    dates_rows = await self._engine.aquery(
        "SELECT DISTINCT date FROM etf_holdings_daily WHERE etf_id = ? ORDER BY date DESC LIMIT 2",
        [etf_id],
    )
    if not dates_rows:
        return {"latest": None, "prior": None, "ops": []}
    latest = dates_rows[0][0]
    if len(dates_rows) < 2:
        return {"latest": str(latest), "prior": None, "ops": []}
    prior = dates_rows[1][0]

    async def _snapshot(d: Any) -> dict[str, dict[str, Any]]:
        rows = await self._engine.aquery(
            "SELECT stock_name, shares_lots, weight_pct FROM etf_holdings_daily WHERE etf_id = ? AND date = ?",
            [etf_id, d],
        )
        return {r[0]: {"shares_lots": r[1], "weight_pct": r[2]} for r in rows}

    cur = await _snapshot(latest)
    prev = await _snapshot(prior)

    ops: list[dict[str, Any]] = []
    for name, c in cur.items():
        p = prev.get(name)
        cur_lots = c.get("shares_lots") or 0
        if p is None:
            ops.append({"stock_name": name, "action": "新增", "shares_delta": cur_lots,
                        "weight_pct": c.get("weight_pct")})
            continue
        prev_lots = p.get("shares_lots") or 0
        delta = cur_lots - prev_lots
        if delta > 0:
            ops.append({"stock_name": name, "action": "加碼", "shares_delta": delta,
                        "weight_pct": c.get("weight_pct")})
        elif delta < 0:
            ops.append({"stock_name": name, "action": "減碼", "shares_delta": delta,
                        "weight_pct": c.get("weight_pct")})
    for name, p in prev.items():
        if name not in cur:
            ops.append({"stock_name": name, "action": "刪除",
                        "shares_delta": -(p.get("shares_lots") or 0), "weight_pct": None})

    ops.sort(key=lambda o: abs(o.get("shares_delta") or 0), reverse=True)
    return {"latest": str(latest), "prior": str(prior), "ops": ops}


async def get_all_stock_prices(self: "MarketDataCache", trade_date: date) -> list[dict[str, Any]]:
    """Fast columnar scan of all stocks for a given date (screener use case)."""
    result = await self._engine.aquery(
        """SELECT stock_id, date, open, high, low, close, volume, amount, spread, turnover
           FROM price_daily WHERE date = ? ORDER BY stock_id""",
        [trade_date],
    )
    return [dict(zip(_PRICE_COLUMNS, row, strict=False)) for row in result]


async def get_price_range_multi(
    self: "MarketDataCache", stock_ids: list[str], start_date: date, end_date: date
) -> dict[str, list[dict[str, Any]]]:
    """Batch read for multiple stocks (avoids N+1 at the DB level)."""
    placeholders = ", ".join(["?"] * len(stock_ids))
    result = await self._engine.aquery(
        f"""SELECT stock_id, date, open, high, low, close, volume, amount, spread, turnover
            FROM price_daily
            WHERE stock_id IN ({placeholders}) AND date >= ? AND date <= ?
            ORDER BY stock_id, date""",
        stock_ids + [start_date, end_date],
    )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in result:
        record = dict(zip(_PRICE_COLUMNS, row, strict=False))
        sid = record["stock_id"]
        grouped.setdefault(sid, []).append(record)
    return grouped


async def count_records(self: "MarketDataCache", table: str = "price_daily") -> int:
    if table not in _VALID_TABLES:
        raise ValueError(f"Invalid table: {table}")
    row = await self._engine.aquery_one(f"SELECT COUNT(*) FROM {table}", None)
    return row[0] if row else 0
