"""TWSE Market endpoints — indices, statistics, foreign investment, listings."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(prefix="/market", tags=["TWSE Market"])


@router.get("/indices", response_model=DataListResponse)
async def get_market_indices() -> dict[str, Any]:
    """Market indices (TAIEX, sector, thematic)."""
    data = await get_twse_client().fetch_report_rows("MI_INDEX")
    return {"data": data, "count": len(data)}


@router.get("/margin", response_model=DataListResponse)
async def get_market_margin(limit: int = Query(50)) -> dict[str, Any]:
    """Market-wide margin/short-selling balances."""
    data = await get_twse_client().fetch_report_rows("MI_MARGN", extra_params={"selectType": "ALL"})
    return {"data": data[:limit], "count": len(data)}


@router.get("/foreign/by-industry", response_model=DataListResponse)
async def get_foreign_by_industry() -> dict[str, Any]:
    """Foreign investment holdings by industry."""
    data = await get_twse_client().fetch_report_rows("MI_QFIIS_cat", fund=True)
    return {"data": data, "count": len(data)}


@router.get("/foreign/top-holdings", response_model=DataListResponse)
async def get_top_foreign_holdings() -> dict[str, Any]:
    """Top 20 stocks held by foreign investors."""
    data = await get_twse_client().fetch_report_rows("MI_QFIIS_sort_20", fund=True)
    return {"data": data, "count": len(data)}


@router.get("/realtime-stats", response_model=DataListResponse)
async def get_realtime_stats(limit: int = Query(20)) -> dict[str, Any]:
    """5-second real-time trading statistics."""
    data = await get_twse_client().fetch_report_rows("MI_5MINS")
    return {"data": data[:limit], "count": len(data)}


@router.get("/daily-summary", response_model=DataListResponse)
async def get_daily_market_summary() -> dict[str, Any]:
    """Market-wide daily trading summary."""
    data = await get_twse_client().fetch_report_rows("FMTQIK")
    return {"data": data, "count": len(data)}


@router.get("/holidays", response_model=DataListResponse)
async def get_market_holidays() -> dict[str, Any]:
    """Trading holiday schedule."""
    data = await get_twse_client().fetch_openapi("/holidaySchedule/holidaySchedule")
    return {"data": data}


@router.get("/listing/new", response_model=DataListResponse)
async def get_new_listings() -> dict[str, Any]:
    """Recently listed companies."""
    data = await get_twse_client().fetch_openapi("/company/newlisting")
    return {"data": data}


@router.get("/listing/suspended", response_model=DataListResponse)
async def get_suspended_listings() -> dict[str, Any]:
    """Suspended/delisted companies."""
    data = await get_twse_client().fetch_openapi("/company/suspendListingCsvAndHtml")
    return {"data": data}


@router.get("/broker/list", response_model=DataListResponse)
async def get_broker_list(limit: int = Query(50)) -> dict[str, Any]:
    """Broker basic information."""
    data = await get_twse_client().fetch_openapi("/opendata/t187ap18")
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/broker/branches", response_model=DataListResponse)
async def get_broker_branches(name: str | None = None, limit: int = Query(50)) -> dict[str, Any]:
    """Broker branch locations."""
    data = await get_twse_client().fetch_openapi("/opendata/OpenData_BRK02")
    if name:
        data = [d for d in data if name in str(d.get("券商名稱", ""))]
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/news/twse", response_model=DataListResponse)
async def get_twse_news() -> dict[str, Any]:
    """TWSE press releases."""
    data = await get_twse_client().fetch_openapi("/news/newsList")
    return {"data": data[:30], "count": len(data[:30])}


@router.get("/news/events", response_model=DataListResponse)
async def get_twse_events() -> dict[str, Any]:
    """TWSE event calendar."""
    data = await get_twse_client().fetch_openapi("/news/eventList")
    return {"data": data[:20], "count": len(data[:20])}
