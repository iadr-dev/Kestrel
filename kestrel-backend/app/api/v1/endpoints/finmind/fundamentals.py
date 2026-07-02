from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_fundamental_service
from app.schemas.common import DataListResponse, ensure_valid_range
from app.services.data.fundamental_service import FundamentalService

router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


@router.get("/{stock_id}/income-statement", response_model=DataListResponse)
async def get_income_statement(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_income_statement(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/balance-sheet", response_model=DataListResponse)
async def get_balance_sheet(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_balance_sheet(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/cash-flow", response_model=DataListResponse)
async def get_cash_flow(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_cash_flow(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/revenue", response_model=DataListResponse)
async def get_revenue(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_revenue(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/dividend", response_model=DataListResponse)
async def get_dividend(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_dividend(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/dividend-result", response_model=DataListResponse)
async def get_dividend_result(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_dividend_result(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/market-value", response_model=DataListResponse)
async def get_market_value(
    stock_id: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_market_value(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/market-value-weight", response_model=DataListResponse)
async def get_market_value_weight(
    stock_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_market_value_weight(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/capital-reduction/{stock_id}", response_model=DataListResponse)
async def get_capital_reduction(
    stock_id: str,
    start_date: date = Query(...),
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_capital_reduction(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/delisted", response_model=DataListResponse)
async def get_delisted(
    service: FundamentalService = Depends(get_fundamental_service),
) -> dict[str, Any]:
    data = await service.get_delisted()
    return {"data": data, "count": len(data)}
