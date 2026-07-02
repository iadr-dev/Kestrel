"""International stock endpoints — FinMind-powered (US/UK/EU/JP prices)."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_international_service
from app.schemas.common import DataListResponse, DataResponse, ensure_valid_range
from app.services.data.international_service import InternationalService

router = APIRouter(prefix="/international", tags=["International"])


@router.get("/us/prices/batch", response_model=DataResponse)
async def get_us_prices_batch(
    ids: str = Query(..., description="Comma-separated US tickers, e.g. AAPL,NVDA,MSFT"),
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    """Daily prices for many US tickers in one request → {data: {ticker: rows}}.

    The screener/watchlist render up to ~30 US sparklines; firing one request per
    ticker trips the per-IP rate limiter. This batches them into a single call (the
    backend fans out to FinMind server-side with bounded concurrency)."""
    tickers = [t.strip().upper() for t in ids.split(",") if t.strip()][:50]
    ensure_valid_range(start_date, end_date)
    data = await service.get_us_prices_batch(tickers, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/us/{stock_id}/price", response_model=DataListResponse)
async def get_us_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_us_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/us/{stock_id}/price/minute", response_model=DataListResponse)
async def get_us_price_minute(
    stock_id: str,
    trade_date: date = Query(...),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    data = await service.get_us_price_minute(stock_id, trade_date)
    return {"data": data, "count": len(data)}


@router.get("/us/info", response_model=DataListResponse)
async def get_us_info(
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    data = await service.get_us_info()
    return {"data": data, "count": len(data)}


@router.get("/uk/{stock_id}/price", response_model=DataListResponse)
async def get_uk_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_uk_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/europe/{stock_id}/price", response_model=DataListResponse)
async def get_europe_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_europe_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/japan/{stock_id}/price", response_model=DataListResponse)
async def get_japan_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: InternationalService = Depends(get_international_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_japan_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}
