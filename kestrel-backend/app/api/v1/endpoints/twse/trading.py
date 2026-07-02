"""TWSE Trading endpoints — daily data, valuation, dividends, warrants, notice/disposal stocks."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/trading", tags=["TWSE Trading"])


@router.get("/daily", response_model=DataListResponse)
async def get_stock_daily_trading(code: str | None = None) -> dict[str, Any]:
    """Latest daily trading data (OHLCV) for all stocks."""
    data = await get_twse_client().fetch_report_rows("STOCK_DAY_ALL")
    if code:
        data = [d for d in data if d.get("證券代號") == code or d.get("Code") == code]
    return {"data": data[:100], "count": len(data)}


@router.get("/monthly-avg", response_model=DataListResponse)
async def get_stock_monthly_average(code: str | None = None) -> dict[str, Any]:
    """Daily close + monthly average prices."""
    data = await get_twse_client().fetch_report_rows("STOCK_DAY_AVG_ALL")
    if code:
        data = [d for d in data if d.get("Code") == code]
    return {"data": data[:100], "count": len(data)}


@router.get("/valuation", response_model=DataListResponse)
async def get_stock_valuation(code: str | None = None) -> dict[str, Any]:
    """P/E ratio, dividend yield, P/B ratio."""
    data = await get_twse_client().fetch_report_rows("BWIBBU_ALL")
    if code:
        data = [d for d in data if d.get("Code") == code]
    return {"data": data[:100], "count": len(data)}


@router.get("/dividend-schedule", response_model=DataListResponse)
async def get_dividend_schedule(code: str | None = None) -> dict[str, Any]:
    """Ex-dividend/rights schedule."""
    data = await get_twse_client().fetch_report_rows("TWT48U_ALL")
    if code:
        data = [d for d in data if d.get("股票代號") == code]
    return {"data": data[:50], "count": len(data)}


@router.get("/top-volume", response_model=DataListResponse)
async def get_top_volume_stocks() -> dict[str, Any]:
    """Top 20 stocks by volume."""
    data = await get_twse_client().fetch_report_rows("MI_INDEX20")
    return {"data": data, "count": len(data)}


@router.get("/notice-stocks", response_model=DataListResponse)
async def get_notice_stocks() -> dict[str, Any]:
    """注意股 — stocks under attention today."""
    data = await get_twse_client().fetch_openapi("/announcement/notice")
    return {"data": data, "count": len(data)}


@router.get("/disposal-stocks", response_model=DataListResponse)
async def get_disposal_stocks(limit: int = Query(50)) -> dict[str, Any]:
    """處置股 — stocks under disciplinary measures."""
    data = await get_twse_client().fetch_openapi("/announcement/punish")
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/gain-loss-stats", response_model=DataListResponse)
async def get_market_gain_loss_stats() -> dict[str, Any]:
    """Market-wide gain/loss statistics."""
    data = await get_twse_client().fetch_openapi("/opendata/twtazu_od")
    return {"data": data}


@router.get("/day-trading-targets", response_model=DataListResponse)
async def get_day_trading_targets() -> dict[str, Any]:
    """Stocks eligible for day trading today."""
    data = await get_twse_client().fetch_report_rows("TWTB4U")
    return {"data": data, "count": len(data)}


@router.get("/warrants", response_model=DataListResponse)
async def get_warrant_info(code: str | None = None, limit: int = Query(50)) -> dict[str, Any]:
    """Warrant basic information."""
    data = await get_twse_client().fetch_openapi("/opendata/t187ap37_L")
    if code:
        data = [d for d in data if d.get("權證代號") == code]
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/warrants/daily", response_model=DataListResponse)
async def get_warrant_daily(code: str | None = None, limit: int = Query(50)) -> dict[str, Any]:
    """Daily warrant trading data."""
    data = await get_twse_client().fetch_openapi("/opendata/t187ap42_L")
    if code:
        data = [d for d in data if d.get("權證代號") == code]
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/block-trades", response_model=DataListResponse)
async def get_block_trades() -> dict[str, Any]:
    """Daily block trade statistics."""
    data = await get_twse_client().fetch_report_rows("BFIAUU_d")
    return {"data": data, "count": len(data)}


@router.get("/after-hours", response_model=DataListResponse)
async def get_after_hours_trading() -> dict[str, Any]:
    """Post-market fixed-price trading."""
    data = await get_twse_client().fetch_report_rows("BFT41U")
    return {"data": data, "count": len(data)}


@router.get("/odd-lot", response_model=DataListResponse)
async def get_odd_lot_trading() -> dict[str, Any]:
    """Odd-lot trading quotes."""
    data = await get_twse_client().fetch_report_rows("TWT53U")
    return {"data": data, "count": len(data)}


@router.get("/suspended", response_model=DataListResponse)
async def get_suspended_stocks() -> dict[str, Any]:
    """Trading halts/resumptions."""
    data = await get_twse_client().fetch_report_rows("TWTAWU")
    return {"data": data, "count": len(data)}


@router.get("/etf-ranking", response_model=DataListResponse)
async def get_etf_ranking() -> dict[str, Any]:
    """ETF regular investment account rankings."""
    data = await get_twse_client().fetch_report_rows("ETFRank")
    return {"data": data, "count": len(data)}
