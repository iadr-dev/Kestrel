"""TWSE History endpoints — historical OHLCV, margin balance, institutional."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/history", tags=["TWSE History"])


@router.get("/stock/{stock_no}", response_model=DataListResponse)
async def get_stock_history(stock_no: str, date: str = Query(..., description="YYYYMMDD")) -> dict[str, Any]:
    """Historical daily OHLCV (monthly chunk, back to 2010)."""
    data = await get_twse_client().get_stock_history(stock_no, date)
    return {"data": data, "count": len(data)}


@router.get("/margin/{stock_no}", response_model=DataListResponse)
async def get_margin_history(stock_no: str, date: str | None = Query(None)) -> dict[str, Any]:
    """Margin/short-selling balance (auto-retries past 7 days for non-trading days)."""
    data = await get_twse_client().get_margin_balance(stock_no, date)
    return {"data": data, "count": len(data)}


@router.get("/margin/all", response_model=DataListResponse)
async def get_margin_all(date: str | None = Query(None), limit: int = Query(50)) -> dict[str, Any]:
    """Market-wide margin balance (all stocks)."""
    data = await get_twse_client().get_margin_balance(None, date)
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/institutional", response_model=DataListResponse)
async def get_institutional_summary(date: str | None = Query(None), limit: int = Query(50)) -> dict[str, Any]:
    """Institutional buy/sell summary (all stocks, sorted by abs net)."""
    data = await get_twse_client().get_institutional_summary(date, limit)
    return {"data": data, "count": len(data)}


@router.get("/institutional/{stock_no}", response_model=DataListResponse)
async def get_institutional_by_stock(stock_no: str, date: str | None = Query(None)) -> dict[str, Any]:
    """Institutional buy/sell detail for a single stock."""
    from datetime import datetime
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    client = get_twse_client()
    raw = await client.fetch_fund_report("T86", params={"response": "json", "date": date, "selectType": "ALL"})
    if not raw or raw.get("stat") != "OK":
        return {"data": []}
    fields = raw.get("fields", [])
    rows = raw.get("data", [])
    all_data = [dict(zip(fields, row, strict=False)) for row in rows]
    filtered = [d for d in all_data if d.get("證券代號", "").strip() == stock_no]
    return {"data": filtered}


@router.get("/valuation", response_model=DataListResponse)
async def get_valuation_by_date(date: str = Query(..., description="YYYYMMDD"), code: str | None = None) -> dict[str, Any]:
    """Historical P/E, P/B, dividend yield by date."""
    client = get_twse_client()
    raw = await client.fetch_exchange_report("BWIBBU_d", params={"response": "json", "date": date, "selectType": "ALL"})
    if isinstance(raw, dict) and raw.get("stat") == "OK":
        fields = raw.get("fields", [])
        rows = raw.get("data", [])
        data = [dict(zip(fields, row, strict=False)) for row in rows]
        if code:
            data = [d for d in data if d.get("證券代號", "").strip() == code]
        return {"data": data[:100], "count": len(data)}
    return {"data": [], "count": 0}
