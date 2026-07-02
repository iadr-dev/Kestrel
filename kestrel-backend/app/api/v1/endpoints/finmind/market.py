from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_market_service
from app.schemas.common import DataListResponse, ensure_valid_range
from app.services.data.market_service import MarketService

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/indices", response_model=DataListResponse)
async def get_indices(
    trade_date: date = Query(..., description="Single trading date"),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    data = await service.get_taiex(trade_date)
    return {"data": data, "count": len(data)}


@router.get("/indices/sector-change", response_model=DataListResponse)
async def get_sector_change(
    start_date: date = Query(...),
    end_date: date = Query(...),
    locale: str = Query("zh-TW"),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    """Compute sector index % change (for the 資金流向 / rotation view).

    The 5-sec index is intraday-only, so after-hours or pre-publish both endpoints
    return empty. To avoid a perpetual loading state, walk `end_date` back to the
    most recent day that HAS 5-sec data, and — when the start day is also empty —
    fall back to that day's INTRADAY change (first vs last snapshot)."""
    from datetime import timedelta as _td

    end_data: list[dict[str, Any]] = []
    for _off in range(8):
        d = end_date - _td(days=_off)
        if d.weekday() >= 5:
            continue
        end_data = await service.get_every_5sec_index(d)
        if end_data:
            break

    if not end_data:
        return {"data": [], "count": 0}

    start_data = await service.get_every_5sec_index(start_date)

    start_map: dict[str, float] = {}
    end_map: dict[str, float] = {}
    if start_data:
        for r in start_data:
            sid = r.get("stock_id", "")
            if sid not in start_map:
                start_map[sid] = r.get("price", 0)
        for r in end_data:
            sid = r.get("stock_id", "")
            end_map[sid] = r.get("price", 0)
    else:
        # Start day has no data → intraday change on the resolved end day:
        # first snapshot per sector = baseline, last = current.
        for r in end_data:
            sid = r.get("stock_id", "")
            if sid not in start_map:
                start_map[sid] = r.get("price", 0)  # first occurrence
            end_map[sid] = r.get("price", 0)         # last occurrence

    from app.core.sector_names import get_sector_name
    results: list[dict[str, Any]] = []
    for sid, end_price in end_map.items():
        start_price = start_map.get(sid)
        if start_price and start_price > 0:
            change = ((end_price - start_price) / start_price) * 100
            results.append({"stock_id": sid, "change": round(change, 2), "sector_name": get_sector_name(sid, locale)})

    results.sort(key=lambda x: abs(x["change"]), reverse=True)
    return {"data": results, "count": len(results)}


@router.get("/indices/5sec", response_model=DataListResponse)
async def get_5sec_index(
    trade_date: date = Query(...),
    locale: str = Query("zh-TW"),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    from datetime import timedelta

    from app.core.sector_names import get_sector_name
    for offset in range(6):
        d = trade_date - timedelta(days=offset)
        data = await service.get_every_5sec_index(d)
        if data:
            for row in data:
                row["sector_name"] = get_sector_name(row.get("stock_id", ""), locale)
            return {"data": data, "count": len(data)}
    return {"data": [], "count": 0}


@router.get("/statistics", response_model=DataListResponse)
async def get_order_book_stats(
    trade_date: date = Query(...),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    data = await service.get_order_book_stats(trade_date)
    return {"data": data, "count": len(data)}


@router.get("/advance-decline", response_model=DataListResponse)
async def get_advance_decline(
    trade_date: date = Query(...),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    """Compute market advance/decline distribution for a trading day."""
    from datetime import timedelta

    from app.core.constants import FinMindDataset
    from app.db.duckdb.engine import get_duckdb

    # A real session has the whole market (~40k stocks). An in-progress intraday /
    # boot ingest can leave a partial day (e.g. 2 rows) as the latest date — walking
    # back and stopping at the first NON-EMPTY day would then compute the whole
    # distribution from those 2 rows (→ "跌 0 / 平盤 2 / 漲 0"). Require a minimum
    # row count so partial days are skipped and we land on the last COMPLETE session.
    MIN_COMPLETE = 500

    # Primary: DuckDB (pre-ingested, always fast). Async aquery so it doesn't
    # block the event loop under concurrency.
    prices = []
    resolved_date: date | None = None
    try:
        db = get_duckdb()
        for offset in range(10):
            d = trade_date - timedelta(days=offset)
            # 4-digit common stocks only — exclude 權證/leveraged ETFs (no ±10%
            # limit, routinely move >10%) which otherwise inflate the limit-up/down
            # tallies and skew the distribution.
            rows = await db.aquery(
                "SELECT stock_id, close, spread FROM price_daily "
                "WHERE date = ? AND close > 0 AND regexp_full_match(stock_id, '[0-9]{4}')",
                [str(d)],
            )
            if len(rows) >= MIN_COMPLETE:
                prices = [{"stock_id": r[0], "close": r[1], "spread": r[2]} for r in rows]
                resolved_date = d
                break
    except Exception:
        pass

    # Fallback: FinMind API (if DuckDB is empty)
    if not prices:
        import re
        provider = service._registry.get_primary("stock_price")
        for offset in range(10):
            d = trade_date - timedelta(days=offset)
            fetched = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_STOCK_PRICE,
                start_date=d,
                end_date=d,
            )
            # Keep only 4-digit common stocks (drop 權證/leveraged ETFs) — matches
            # the DuckDB path so the distribution is computed over the same universe.
            common = [p for p in fetched if re.fullmatch(r"\d{4}", str(p.get("stock_id", "")))]
            if len(common) >= MIN_COMPLETE:
                prices = common
                resolved_date = d
                break

    # Compute distribution
    buckets: list[dict[str, Any]] = [
        {"b": "<-5%", "n": 0, "up": False},
        {"b": "-5~-3", "n": 0, "up": False},
        {"b": "-3~-2", "n": 0, "up": False},
        {"b": "-2~-1", "n": 0, "up": False},
        {"b": "-1~0", "n": 0, "up": False},
        {"b": "flat", "n": 0, "flat": True},
        {"b": "0~1", "n": 0, "up": True},
        {"b": "1~2", "n": 0, "up": True},
        {"b": "2~3", "n": 0, "up": True},
        {"b": "3~5", "n": 0, "up": True},
        {"b": ">5%", "n": 0, "up": True},
    ]

    limit_up = 0
    limit_down = 0
    total = 0

    for p in prices:
        close = p.get("close", 0)
        spread = p.get("spread")
        if not close or spread is None:
            continue
        total += 1
        prev = close - spread
        if prev == 0:
            continue
        pct = (spread / prev) * 100

        if pct <= -5:
            buckets[0]["n"] += 1
        elif pct <= -3:
            buckets[1]["n"] += 1
        elif pct <= -2:
            buckets[2]["n"] += 1
        elif pct <= -1:
            buckets[3]["n"] += 1
        elif pct < 0:
            buckets[4]["n"] += 1
        elif pct == 0:
            buckets[5]["n"] += 1
        elif pct < 1:
            buckets[6]["n"] += 1
        elif pct < 2:
            buckets[7]["n"] += 1
        elif pct < 3:
            buckets[8]["n"] += 1
        elif pct < 5:
            buckets[9]["n"] += 1
        else:
            buckets[10]["n"] += 1

        if pct >= 9.5:
            limit_up += 1
        elif pct <= -9.5:
            limit_down += 1

    up_count = sum(b["n"] for b in buckets if b.get("up"))
    down_count = sum(b["n"] for b in buckets if not b.get("up") and not b.get("flat"))

    return {
        "data": buckets,
        "summary": {
            "up": up_count,
            "down": down_count,
            "flat": buckets[5]["n"],
            "total": total,
            "limit_up": limit_up,
            "limit_down": limit_down,
        },
        # The actual session the numbers describe (may be earlier than the requested
        # trade_date when today's session hasn't completed) so the UI labels it right.
        "trade_date": str(resolved_date) if resolved_date else str(trade_date),
    }


@router.get("/advance-decline/history", response_model=DataListResponse)
async def get_advance_decline_history(
    trade_date: date = Query(...),
    days: int = Query(20, ge=1, le=60),
) -> dict[str, Any]:
    """Per-day advance/decline counts over the last `days` COMPLETE sessions.

    Powers the 漲跌家數 history chart, which needs a time series of
    {date, up, down, limit_up, limit_down} — the single-day /advance-decline
    distribution can't supply that. Computed in one grouped DuckDB scan over
    price_daily (TW ±10% daily limit → |pct| ≥ 9.5% counts as limit up/down).
    """
    from app.db.duckdb.engine import get_duckdb

    # Only sessions whose row count clears the completeness bar (≥500) — skips
    # partial intraday/boot days so the series isn't polluted by 2-row dates.
    rows = []
    try:
        db = get_duckdb()
        rows = await db.aquery(
            """
            WITH complete AS (
                SELECT date FROM price_daily
                GROUP BY date HAVING COUNT(*) >= 500
                ORDER BY date DESC LIMIT ?
            )
            SELECT p.date,
                   SUM(CASE WHEN p.spread > 0 THEN 1 ELSE 0 END) AS up,
                   SUM(CASE WHEN p.spread < 0 THEN 1 ELSE 0 END) AS down,
                   SUM(CASE WHEN p.spread = 0 THEN 1 ELSE 0 END) AS unchanged,
                   SUM(CASE WHEN p.close > 0 AND (p.close - p.spread) > 0
                            AND p.spread / (p.close - p.spread) >= 0.095 THEN 1 ELSE 0 END) AS limit_up,
                   SUM(CASE WHEN p.close > 0 AND (p.close - p.spread) > 0
                            AND p.spread / (p.close - p.spread) <= -0.095 THEN 1 ELSE 0 END) AS limit_down
            FROM price_daily p
            JOIN complete c ON p.date = c.date
            -- 漲跌家數 counts listed common stocks only. Restrict to 4-digit codes
            -- so warrants / leveraged ETFs (no ±10% limit, routinely move >10%)
            -- don't massively inflate the limit-up/down tallies.
            WHERE p.close > 0 AND p.spread IS NOT NULL AND p.date <= ?
              AND regexp_full_match(p.stock_id, '[0-9]{4}')
            GROUP BY p.date
            ORDER BY p.date
            """,
            [days, str(trade_date)],
        )
    except Exception:
        rows = []

    data = [
        {
            "date": str(r[0]),
            "up": int(r[1] or 0),
            "down": int(r[2] or 0),
            "unchanged": int(r[3] or 0),
            "limit_up": int(r[4] or 0),
            "limit_down": int(r[5] or 0),
        }
        for r in rows
    ]
    return {"data": data, "count": len(data)}


@router.get("/total-return", response_model=DataListResponse)
async def get_total_return(
    data_id: str = Query(..., description="TAIEX or TPEx"),
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MarketService = Depends(get_market_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_total_return_index(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}
