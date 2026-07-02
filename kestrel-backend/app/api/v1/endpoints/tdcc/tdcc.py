"""TDCC data endpoints — shareholding distribution from TDCC OpenAPI."""

from typing import Any

from fastapi import APIRouter

from app.providers.tdcc import get_tdcc_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/tdcc", tags=["TDCC"])


@router.get("/shareholding/{stock_id}", response_model=DataListResponse)
async def get_shareholding(stock_id: str) -> dict[str, Any]:
    """Get TDCC shareholding distribution by tier (集保戶股權分散表)."""
    try:
        client = get_tdcc_client()
        data = await client.get_shareholding(stock_id)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/securities-info/{stock_id}", response_model=DataListResponse)
async def get_securities_info(stock_id: str) -> dict[str, Any]:
    """Get TDCC securities basic info (證券基本資料)."""
    try:
        client = get_tdcc_client()
        data = await client.get_securities_info(stock_id)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/director-shareholding/{stock_id}", response_model=DataListResponse)
async def get_director_shareholding(stock_id: str) -> dict[str, Any]:
    """Get director/supervisor custody data (董監分戶保管)."""
    try:
        client = get_tdcc_client()
        data = await client.get_director_shareholding(stock_id)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/monthly-changes/{stock_id}", response_model=DataListResponse)
async def get_monthly_changes(stock_id: str, market: str = "listed") -> dict[str, Any]:
    """Get monthly custody change analysis (個別股票異動月分析表)."""
    try:
        client = get_tdcc_client()
        data = await client.get_monthly_changes(stock_id, market)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/weekly-balance/{stock_id}", response_model=DataListResponse)
async def get_weekly_balance(stock_id: str, market: str = "listed") -> dict[str, Any]:
    """Get weekly custody balance (保管有價證券週餘額表)."""
    try:
        client = get_tdcc_client()
        data = await client.get_weekly_balance(stock_id, market)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}
