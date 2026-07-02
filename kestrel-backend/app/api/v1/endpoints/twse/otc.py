"""TPEx (OTC) endpoints — daily prices, institutional, P/E ratios."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/otc", tags=["TWSE OTC"])


@router.get("/daily", response_model=DataListResponse)
async def get_otc_daily(code: str | None = None, limit: int = Query(50)) -> dict[str, Any]:
    """OTC daily close prices (all stocks or filtered by code)."""
    data = await get_twse_client().get_otc_daily(code, limit)
    return {"data": data, "count": len(data)}


@router.get("/institutional", response_model=DataListResponse)
async def get_otc_institutional() -> dict[str, Any]:
    """OTC institutional buy/sell (foreign/trust/dealer)."""
    data = await get_twse_client().get_otc_institutional()
    return {"data": data, "count": len(data)}


@router.get("/pe-ratio", response_model=DataListResponse)
async def get_otc_pe_ratio() -> dict[str, Any]:
    """OTC P/E ratios for all OTC stocks."""
    data = await get_twse_client().get_otc_pe_ratio()
    return {"data": data, "count": len(data)}
