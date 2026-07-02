"""TWSE Real-time endpoints — MIS intraday quotes."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/realtime", tags=["TWSE Realtime"])


@router.get("/quote", response_model=DataListResponse)
async def get_realtime_quote(codes: str = Query(..., description="Comma-separated stock codes (e.g. 2330,2317,2454)")) -> dict[str, Any]:
    """Real-time intraday quotes from MIS (supports multiple stocks, auto-detects TWSE/OTC)."""
    stock_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = await get_twse_client().get_realtime_quote(stock_list)
    return {"data": data, "count": len(data)}
