from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_macro_service
from app.schemas.common import DataListResponse, DataResponse, ensure_valid_range
from app.services.data.macro_service import MacroService

router = APIRouter(prefix="/macro", tags=["Macro"])


@router.get("/exchange-rate/{currency}", response_model=DataListResponse)
async def get_exchange_rate(
    currency: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_exchange_rate(currency, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/interest-rate/{country}", response_model=DataListResponse)
async def get_interest_rate(
    country: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_interest_rate(country, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/gold", response_model=DataListResponse)
async def get_gold(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_gold_price(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/oil/{oil_type}", response_model=DataListResponse)
async def get_oil(
    oil_type: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_oil_price(oil_type, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/bonds/yield-curve", response_model=DataResponse)
async def get_yield_curve(
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    """Get full US Treasury yield curve (all tenors, latest values)."""
    import asyncio
    tenors = [
        "United States 1-Month", "United States 3-Month", "United States 6-Month",
        "United States 1-Year", "United States 2-Year", "United States 3-Year",
        "United States 5-Year", "United States 7-Year", "United States 10-Year",
        "United States 20-Year", "United States 30-Year",
    ]
    labels = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    from datetime import timedelta
    start = date.today() - timedelta(days=35)

    async def fetch_tenor(t: str) -> list[dict[str, Any]]:
        data = await service.get_bond_yield(t, start, None)
        return data

    results = await asyncio.gather(*[fetch_tenor(t) for t in tenors])

    current: list[dict[str, Any]] = []
    week_ago: list[dict[str, Any]] = []
    month_ago: list[dict[str, Any]] = []

    for i, data in enumerate(results):
        if not data:
            current.append({"label": labels[i], "value": None})
            week_ago.append({"label": labels[i], "value": None})
            month_ago.append({"label": labels[i], "value": None})
            continue
        latest = data[-1]
        current.append({"label": labels[i], "value": latest.get("value")})
        # Find ~7 days ago
        w = next((r for r in reversed(data) if r.get("date", "") <= str(date.today() - timedelta(days=7))), None)
        week_ago.append({"label": labels[i], "value": w.get("value") if w else None})
        # Find ~30 days ago
        m = next((r for r in reversed(data) if r.get("date", "") <= str(date.today() - timedelta(days=30))), None)
        month_ago.append({"label": labels[i], "value": m.get("value") if m else None})

    return {
        "data": {
            "current": current,
            "week_ago": week_ago,
            "month_ago": month_ago,
        }
    }


@router.get("/bonds/{maturity}", response_model=DataListResponse)
async def get_bonds(
    maturity: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_bond_yield(maturity, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/fear-greed", response_model=DataListResponse)
async def get_fear_greed(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_fear_greed(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/business-indicator", response_model=DataListResponse)
async def get_business_indicator(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: MacroService = Depends(get_macro_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_business_indicator(start_date, end_date)
    return {"data": data, "count": len(data)}
