from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.db.duckdb.engine import get_duckdb
from app.dependencies import get_institutional_service
from app.schemas.common import DataListResponse, DataResponse, ensure_valid_range
from app.services.data.institutional_service import InstitutionalService

router = APIRouter(prefix="/institutional", tags=["Institutional"])


@router.get("/buy-sell/total", response_model=DataListResponse)
async def get_total_buy_sell(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_total_buy_sell(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/buy-sell/{stock_id}", response_model=DataListResponse)
async def get_buy_sell(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_buy_sell(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/foreign-holding/{stock_id}", response_model=DataListResponse)
async def get_foreign_holding(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_foreign_holding(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/shareholding-per/{stock_id}", response_model=DataListResponse)
async def get_shareholding_per(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_holding_shares_per(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/holding-distribution/{stock_id}", response_model=DataResponse)
async def get_holding_distribution(
    stock_id: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    """TDCC 集保 shareholding distribution for the stock detail 籌碼 → 大戶資訊 tab:
    per-level breakdown, retail/mid/whale buckets, 千張大戶 %, holder count, and a
    weekly concentration trend. Defaults to the last ~12 weeks."""
    from datetime import timedelta
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    ensure_valid_range(start_date, end_date)
    data = await service.get_holding_distribution(stock_id, start_date, end_date)
    return {"data": data}


@router.get("/board-holdings/{stock_id}", response_model=DataListResponse)
async def get_board_holdings(stock_id: str) -> dict[str, Any]:
    """Board/supervisor shareholding balances (董監事持股餘額) for the 持股人 tab —
    one row per director/supervisor with title, current shares, and pledge ratio.
    Sourced from the live TWSE OpenAPI (t187ap11_L); replaces the empty yfinance
    holders feed that returned nothing for Taiwan tickers."""
    from app.providers.mops import get_mops_client
    rows = await get_mops_client().get_director_holdings(stock_id)
    return {"data": rows, "count": len(rows)}


@router.get("/margin/total", response_model=DataListResponse)
async def get_total_margin(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_total_margin(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/margin/{stock_id}", response_model=DataListResponse)
async def get_margin(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_margin(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/margin-maintenance", response_model=DataListResponse)
async def get_margin_maintenance(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_margin_maintenance(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/securities-lending/{stock_id}", response_model=DataListResponse)
async def get_securities_lending(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_securities_lending(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/short-sale-balances/{stock_id}", response_model=DataListResponse)
async def get_short_sale_balances(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_short_sale_balances(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/trading-daily-report", response_model=DataListResponse)
async def get_trading_daily_report(
    stock_id: str | None = Query(None),
    securities_trader_id: str | None = Query(None),
    report_date: date | None = Query(None, description="Single date (Sponsor tier)"),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    data = await service.get_trading_daily_report(
        stock_id=stock_id, securities_trader_id=securities_trader_id, report_date=report_date
    )
    return {"data": data, "count": len(data)}


@router.get("/trading-daily-report/agg", response_model=DataListResponse)
async def get_trading_report_agg(
    stock_id: str = Query(...),
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_trading_report_agg(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/government-bank", response_model=DataListResponse)
async def get_government_bank(
    start_date: date = Query(...),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    """Per-stock government-bank (官股券商) net buy/sell ranking for the last
    available trading day on/before start_date. Aggregated so the UI can show the
    stocks government banks moved most, with the actual session date labelled."""
    result = await service.get_government_bank_ranking(start_date)
    data = result["data"]
    return {"data": data, "count": len(data), "trade_date": result["trade_date"]}


@router.get("/ranking", response_model=DataListResponse)
async def get_institutional_ranking(
    start_date: date = Query(..., description="Anchor date; walks back to the last session with data"),
    investor: str = Query("all", description="all (三大法人) | foreign (外資) | trust (投信) | dealer (自營商)"),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    """Per-stock institutional net buy/sell ranking by investor group, for the last
    available trading day on/before start_date. Powers the market-page 買賣排行 card
    (法人/外資/投信, 買超/賣超). Sorted by net shares descending — the UI reads the top
    for 買超 and the bottom for 賣超. The all-stocks dataset (~100k rows/day) is
    aggregated server-side, so the client receives only the trimmed ranking."""
    result = await service.get_institutional_ranking(start_date, investor=investor)
    data = result["data"]
    return {"data": data, "count": len(data), "trade_date": result["trade_date"]}


@router.get("/block-trade/{stock_id}", response_model=DataListResponse)
async def get_block_trade(
    stock_id: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_block_trade(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/disposition/all", response_model=DataResponse)
async def get_all_dispositions(
    start_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    """Get all disposition stocks with computed categories + live price/volume/institutional data."""
    from datetime import timedelta

    if not start_date:
        start_date = date.today() - timedelta(days=90)

    data = await service.get_disposition(None, start_date, None)
    today = date.today()

    risk: list[dict[str, Any]] = []
    locked: list[dict[str, Any]] = []
    releasing: list[dict[str, Any]] = []
    warning: list[dict[str, Any]] = []

    seen_stocks: set[str] = set()
    active_stocks: list[dict[str, Any]] = []

    for row in data:
        period_start = row.get("period_start") or row.get("date", "")
        period_end = row.get("period_end", "")

        try:
            p_start = date.fromisoformat(period_start) if period_start else None
            p_end = date.fromisoformat(period_end) if period_end else None
        except (ValueError, TypeError):
            continue

        if not p_start or not p_end:
            continue

        stock_id = row.get("stock_id", "")
        if stock_id in seen_stocks:
            continue
        seen_stocks.add(stock_id)

        remaining_days = (p_end - today).days
        if remaining_days < 0:
            continue

        enriched = {
            **row,
            "remaining_days": remaining_days,
            "total_days": (p_end - p_start).days,
        }
        active_stocks.append(enriched)

    # Enrich with price + institutional data from DuckDB
    price_map = await _get_latest_prices(list(seen_stocks))
    inst_map = await _get_latest_institutional(list(seen_stocks))

    for item in active_stocks:
        sid = item.get("stock_id", "")
        price_info = price_map.get(sid, {})
        inst_info = inst_map.get(sid, {})

        item["close"] = price_info.get("close")
        item["change"] = price_info.get("spread")
        item["change_pct"] = (
            round((price_info["spread"] / (price_info["close"] - price_info["spread"])) * 100, 2)
            if price_info.get("close") and price_info.get("spread") and (price_info["close"] - price_info["spread"]) != 0
            else None
        )
        # OHLC + sparkline for the row's candlestick + mini-kline.
        item["open"] = price_info.get("open")
        item["high"] = price_info.get("high")
        item["low"] = price_info.get("low")
        item["spark"] = price_info.get("spark", [])
        item["volume"] = price_info.get("volume")
        item["turnover"] = price_info.get("amount")
        item["turnover_rate"] = price_info.get("turnover")
        item["institutional_net"] = inst_info.get("net")
        item["foreign_net"] = inst_info.get("foreign_net")
        item["trust_net"] = inst_info.get("trust_net")
        item["dealer_net"] = inst_info.get("dealer_net")

        if item["remaining_days"] <= 3:
            releasing.append(item)
        else:
            locked.append(item)

    # Risk tab: stocks with multiple dispositions (repeat offenders)
    disposition_counts: dict[str, int] = {}
    for row in data:
        sid = row.get("stock_id", "")
        disposition_counts[sid] = disposition_counts.get(sid, 0) + 1
    for item in locked + releasing:
        sid = item.get("stock_id", "")
        if disposition_counts.get(sid, 0) > 1:
            risk.append({**item, "fastest_days": item.get("remaining_days", 0)})

    locked.sort(key=lambda x: x.get("remaining_days", 999))
    releasing.sort(key=lambda x: x.get("remaining_days", 999))

    return {
        "data": {
            "risk": risk,
            "locked": locked,
            "releasing": releasing,
            "warning": warning,
        },
        "summary": {
            "locked_count": len(locked),
            "releasing_count": len(releasing),
            "risk_count": len(risk),
            "warning_count": len(warning),
        },
    }


async def _get_latest_prices(stock_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch latest OHLC bar + a recent close sparkline for disposition stocks from
    DuckDB — enough to render a candlestick + mini-kline per row in the UI."""
    if not stock_ids:
        return {}
    try:
        db = get_duckdb()
        placeholders = ",".join(["?" for _ in stock_ids])
        # Per-stock latest bar. The subquery MUST reference the OUTER row via an
        # explicit alias (p.stock_id) — an un-aliased `price_daily.stock_id` inside
        # the subquery binds to the SUBQUERY's own table (self-reference), making it
        # WHERE stock_id = stock_id (always true) → MAX(date) becomes the GLOBAL max,
        # so any stock whose latest bar predates the global max (e.g. only trades to
        # 6/24 while the market's max is 6/25) matched nothing → blank price/volume.
        rows = await db.aquery(f"""
            SELECT stock_id, open, high, low, close, spread, volume, amount, turnover
            FROM price_daily p
            WHERE stock_id IN ({placeholders})
              AND date = (SELECT MAX(date) FROM price_daily WHERE stock_id = p.stock_id)
            ORDER BY stock_id
        """, stock_ids)

        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            result[row[0]] = {
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "spread": row[5],
                "volume": row[6],
                "amount": row[7],
                "turnover": row[8],
                "spark": [],
            }

        # Recent close series (oldest→newest) for the mini-kline — last 20 bars.
        spark_rows = await db.aquery(f"""
            WITH recent AS (
                SELECT stock_id, date, close,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM price_daily
                WHERE stock_id IN ({placeholders}) AND close > 0
            )
            SELECT stock_id, close FROM recent WHERE rn <= 20 ORDER BY stock_id, date
        """, stock_ids)
        for sid, close in spark_rows:
            if sid in result:
                result[sid]["spark"].append(close)
        return result
    except Exception:
        return {}


async def _get_latest_institutional(stock_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch latest institutional net buy/sell for disposition stocks from DuckDB."""
    if not stock_ids:
        return {}
    try:
        db = get_duckdb()
        placeholders = ",".join(["?" for _ in stock_ids])
        rows = await db.aquery(f"""
            SELECT stock_id, institution, buy, sell
            FROM institutional_daily
            WHERE stock_id IN ({placeholders})
              AND date = (SELECT MAX(date) FROM institutional_daily)
        """, stock_ids)

        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            sid, institution, buy, sell = row
            if sid not in result:
                result[sid] = {"net": 0, "foreign_net": 0, "trust_net": 0, "dealer_net": 0}
            net = (buy or 0) - (sell or 0)
            result[sid]["net"] += net
            if "Foreign" in (institution or "") or "外資" in (institution or ""):
                result[sid]["foreign_net"] += net
            elif "Investment_Trust" in (institution or "") or "投信" in (institution or ""):
                result[sid]["trust_net"] += net
            elif "Dealer" in (institution or "") or "自營" in (institution or ""):
                result[sid]["dealer_net"] += net
        return result
    except Exception:
        return {}


@router.get("/disposition/{stock_id}", response_model=DataListResponse)
async def get_disposition(
    stock_id: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: InstitutionalService = Depends(get_institutional_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_disposition(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}
