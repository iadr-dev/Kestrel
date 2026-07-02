from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_derivative_service
from app.schemas.common import DataListResponse, ensure_valid_range
from app.services.data.derivative_service import DerivativeService

router = APIRouter(prefix="/derivatives", tags=["Derivatives"])


@router.get("/futures/{futures_id}/daily", response_model=DataListResponse)
async def get_futures_daily(
    futures_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_daily(futures_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/{futures_id}/tick", response_model=DataListResponse)
async def get_futures_tick(
    futures_id: str,
    trade_date: date = Query(...),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    data = await service.get_futures_tick(futures_id, trade_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/institutional", response_model=DataListResponse)
async def get_futures_institutional(
    data_id: str | None = Query(None, description="e.g. TX"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_institutional(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/institutional/after-hours", response_model=DataListResponse)
async def get_futures_institutional_after_hours(
    data_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_institutional_after_hours(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/large-traders", response_model=DataListResponse)
async def get_futures_large_traders(
    data_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_large_traders(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/{futures_id}/spread", response_model=DataListResponse)
async def get_futures_spread(
    futures_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_spread(futures_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/futures/{futures_id}/settlement", response_model=DataListResponse)
async def get_futures_settlement(
    futures_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_futures_settlement(futures_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/options/{option_id}/daily", response_model=DataListResponse)
async def get_options_daily(
    option_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_options_daily(option_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/options/{option_id}/tick", response_model=DataListResponse)
async def get_options_tick(
    option_id: str,
    trade_date: date = Query(...),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    data = await service.get_options_tick(option_id, trade_date)
    return {"data": data, "count": len(data)}


@router.get("/options/institutional", response_model=DataListResponse)
async def get_options_institutional(
    data_id: str | None = Query(None, description="e.g. TXO"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_options_institutional(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/options/institutional/after-hours", response_model=DataListResponse)
async def get_options_institutional_after_hours(
    data_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_options_institutional_after_hours(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/options/large-traders", response_model=DataListResponse)
async def get_options_large_traders(
    data_id: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_options_large_traders(data_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/options/{option_id}/settlement", response_model=DataListResponse)
async def get_options_settlement(
    option_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_options_settlement(option_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/snapshot/futures", response_model=DataListResponse)
async def get_futures_snapshot(
    data_id: str | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    data = await service.get_futures_snapshot(data_id)
    return {"data": data, "count": len(data)}


@router.get("/snapshot/options", response_model=DataListResponse)
async def get_options_snapshot(
    data_id: str | None = Query(None),
    service: DerivativeService = Depends(get_derivative_service),
) -> dict[str, Any]:
    data = await service.get_options_snapshot(data_id)
    return {"data": data, "count": len(data)}
