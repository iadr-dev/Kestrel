"""TAIFEX endpoints — futures/options positions, analytics, margin."""

from typing import Any

from fastapi import APIRouter

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/taifex", tags=["TWSE TAIFEX"])


@router.get("/institutional", response_model=DataListResponse)
async def get_taifex_institutional() -> dict[str, Any]:
    """Futures/options institutional positions (foreign/trust/dealer)."""
    data = await get_twse_client().get_futures_institutional()
    return {"data": data, "count": len(data)}


@router.get("/position", response_model=DataListResponse)
async def get_taifex_position() -> dict[str, Any]:
    """Futures open interest by contract."""
    data = await get_twse_client().get_futures_position()
    return {"data": data, "count": len(data)}


@router.get("/put-call-ratio", response_model=DataListResponse)
async def get_taifex_put_call_ratio() -> dict[str, Any]:
    """Put/call ratio analysis."""
    data = await get_twse_client().get_put_call_ratio()
    return {"data": data, "count": len(data)}


@router.get("/large-traders", response_model=DataListResponse)
async def get_taifex_large_traders() -> dict[str, Any]:
    """Large trader open interest positions."""
    data = await get_twse_client().get_large_traders_oi()
    return {"data": data, "count": len(data)}


@router.get("/options-analytics", response_model=DataListResponse)
async def get_taifex_options_analytics() -> dict[str, Any]:
    """Options analytics (delta, OI changes)."""
    data = await get_twse_client().get_options_analytics()
    return {"data": data, "count": len(data)}


@router.get("/daily-report", response_model=DataListResponse)
async def get_taifex_daily_report() -> dict[str, Any]:
    """Daily futures market report."""
    data = await get_twse_client().get_taifex_daily_report()
    return {"data": data, "count": len(data)}


@router.get("/margin", response_model=DataListResponse)
async def get_taifex_margin_req() -> dict[str, Any]:
    """Margin requirements by contract."""
    data = await get_twse_client().get_taifex_margin()
    return {"data": data, "count": len(data)}


@router.get("/trading-stats", response_model=DataListResponse)
async def get_taifex_trading_stats() -> dict[str, Any]:
    """Trading volume and OI statistics."""
    data = await get_twse_client().get_taifex_trading_stats()
    return {"data": data, "count": len(data)}
