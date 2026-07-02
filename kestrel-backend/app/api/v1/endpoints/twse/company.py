"""TWSE Company endpoints — profiles, financials, ESG, governance."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter(prefix="/company", tags=["TWSE Company"])


@router.get("/profile/{code}", response_model=DataResponse)
async def get_company_profile(code: str) -> dict[str, Any]:
    """Company basic profile (industry, address, capital)."""
    data = await get_twse_client().fetch_company("/opendata/t187ap03_L", code)
    return {"data": data}


@router.get("/dividend/{code}", response_model=DataResponse)
async def get_company_dividend(code: str) -> dict[str, Any]:
    """Company dividend history."""
    data = await get_twse_client().fetch_company("/opendata/t187ap45_L", code)
    return {"data": data}


@router.get("/revenue/{code}", response_model=DataResponse)
async def get_company_monthly_revenue(code: str) -> dict[str, Any]:
    """Company monthly revenue."""
    data = await get_twse_client().fetch_company("/opendata/t187ap05_L", code)
    return {"data": data}


@router.get("/major-shareholders/{code}", response_model=DataResponse)
async def get_company_major_shareholders(code: str) -> dict[str, Any]:
    """Major shareholders (>10% ownership)."""
    data = await get_twse_client().fetch_company("/opendata/t187ap02_L", code)
    return {"data": data}


@router.get("/board-shareholdings/{code}", response_model=DataResponse)
async def get_company_board_shareholdings(code: str) -> dict[str, Any]:
    """Board member shareholdings."""
    data = await get_twse_client().fetch_company("/opendata/t187ap11_L", code)
    return {"data": data}


@router.get("/news", response_model=DataListResponse)
async def get_company_major_news(code: str | None = None, limit: int = Query(50)) -> dict[str, Any]:
    """Major company announcements."""
    data = await get_twse_client().fetch_openapi("/opendata/t187ap04_L")
    if code:
        data = [d for d in data if d.get("公司代號") == code]
    return {"data": data[:limit], "count": len(data[:limit])}


@router.get("/financials/income/{code}", response_model=DataResponse)
async def get_company_income_statement(code: str) -> dict[str, Any]:
    """Company income statement (auto-detects industry)."""
    client = get_twse_client()
    for suffix in ["_ci", "_basi", "_bd", "_fh", "_ins", "_mim"]:
        data = await client.fetch_company(f"/opendata/t187ap06_L{suffix}", code)
        if data:
            return {"data": data}
    return {"data": None}


@router.get("/financials/balance/{code}", response_model=DataResponse)
async def get_company_balance_sheet(code: str) -> dict[str, Any]:
    """Company balance sheet (auto-detects industry)."""
    client = get_twse_client()
    for suffix in ["_ci", "_basi", "_bd", "_fh", "_ins", "_mim"]:
        data = await client.fetch_company(f"/opendata/t187ap07_L{suffix}", code)
        if data:
            return {"data": data}
    return {"data": None}


@router.get("/profitability/{code}", response_model=DataResponse)
async def get_company_profitability(code: str) -> dict[str, Any]:
    """Company profitability analysis (margins, ROE)."""
    data = await get_twse_client().fetch_company("/opendata/t187ap17_L", code)
    return {"data": data}


@router.get("/esg/{code}/{topic}", response_model=DataResponse)
async def get_company_esg(code: str, topic: int) -> dict[str, Any]:
    """Company ESG data by topic (1=greenhouse, 2=energy, 3=water, ..., 9=governance, etc.)."""
    data = await get_twse_client().fetch_company(f"/opendata/t187ap46_L_{topic}", code)
    return {"data": data}


@router.get("/governance/{code}", response_model=DataResponse)
async def get_company_governance(code: str) -> dict[str, Any]:
    """Company corporate governance."""
    data = await get_twse_client().fetch_company("/opendata/t187ap46_L_9", code)
    return {"data": data}
