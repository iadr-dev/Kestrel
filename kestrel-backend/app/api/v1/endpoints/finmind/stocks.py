from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_stock_service
from app.schemas.common import DataListResponse, ensure_valid_range
from app.services.data.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/{stock_id}/price", response_model=DataListResponse)
async def get_stock_price(
    stock_id: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date"),
    indicators: list[str] = Query(default=[], description="Indicator names (sma, ema, macd, kd, rsi, bollinger)"),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    if indicators:
        indicator_specs = [{"name": i, "params": {}} for i in indicators]
        return await service.get_price_with_indicators(stock_id, start_date, end_date, indicator_specs)
    ensure_valid_range(start_date, end_date)
    data = await service.get_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/price/adjusted", response_model=DataListResponse)
async def get_adjusted_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_price_adjusted(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/price/tick", response_model=DataListResponse)
async def get_price_tick(
    stock_id: str,
    trade_date: date = Query(..., description="Single trading date"),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    data = await service.get_price_tick(stock_id, trade_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/price/kbar", response_model=DataListResponse)
async def get_kbar(
    stock_id: str,
    trade_date: date = Query(..., description="Single trading date (Sponsor tier)"),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    data = await service.get_kbar(stock_id, trade_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/price/week", response_model=DataListResponse)
async def get_week_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_week_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/price/month", response_model=DataListResponse)
async def get_month_price(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_month_price(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/info/all", response_model=DataListResponse)
async def get_all_stock_info(
    limit: int | None = Query(None, ge=1, le=10000, description="Max rows to return (default: all)"),
    offset: int = Query(0, ge=0),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    """Get all stock info (for search autocomplete).

    Optional limit/offset for pagination. `total` is the full count; `data`/`count`
    reflect the returned page. Defaults preserve the previous "return all" behaviour.
    """
    data = await service.get_stock_info()
    total = len(data)
    if limit is not None:
        data = data[offset:offset + limit]
    elif offset:
        data = data[offset:]
    return {"data": data, "count": len(data), "total": total}


@router.get("/{stock_id}/info", response_model=DataListResponse)
async def get_stock_info(
    stock_id: str,
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    """Get info for a specific stock."""
    all_stocks = await service.get_stock_info()
    filtered = [s for s in all_stocks if s.get("stock_id") == stock_id]
    return {"data": filtered, "count": len(filtered)}


@router.get("/{stock_id}/per", response_model=DataListResponse)
async def get_per(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_per(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/snapshot", response_model=DataListResponse)
async def get_snapshot(
    stock_id: str,
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    data = await service.get_snapshot(stock_id)
    return {"data": data, "count": len(data)}


@router.get("/snapshot/all", response_model=DataListResponse)
async def get_all_snapshots(
    limit: int | None = Query(None, ge=1, le=10000, description="Max rows to return (default: all)"),
    offset: int = Query(0, ge=0),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    """Real-time snapshot for all stocks. Optional limit/offset; `total` is the
    full count, `data`/`count` reflect the returned page."""
    data = await service.get_snapshot(None)
    total = len(data)
    if limit is not None:
        data = data[offset:offset + limit]
    elif offset:
        data = data[offset:]
    return {"data": data, "count": len(data), "total": total}


@router.get("/trading-dates", response_model=DataListResponse)
async def get_trading_dates(
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    data = await service.get_trading_dates()
    return {"data": data, "count": len(data)}


@router.get("/price-limits", response_model=DataListResponse)
async def get_price_limits(
    stock_id: str | None = Query(None),
    start_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    data = await service.get_price_limits(stock_id, start_date)
    return {"data": data, "count": len(data)}


@router.get("/day-trading/{stock_id}", response_model=DataListResponse)
async def get_day_trading(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_day_trading(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/suspended", response_model=DataListResponse)
async def get_suspended(
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_suspended(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/10-year/{stock_id}", response_model=DataListResponse)
async def get_10_year(
    stock_id: str,
    start_date: date = Query(...),
    end_date: date | None = Query(None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    ensure_valid_range(start_date, end_date)
    data = await service.get_10_year(stock_id, start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/news/market", response_model=DataListResponse)
async def get_market_news(
    start_date: date = Query(default=None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    """Get market-wide news (all stocks, no data_id filter)."""
    data = await service.get_market_news(start_date)
    return {"data": data, "count": len(data)}


@router.get("/{stock_id}/news", response_model=DataListResponse)
async def get_stock_news(
    stock_id: str,
    start_date: date = Query(default=None),
    service: StockService = Depends(get_stock_service),
) -> dict[str, Any]:
    """Get stock news from FinMind TaiwanStockNews with thumbnails."""
    data = await service.get_stock_news(stock_id, start_date)
    return {"data": data, "count": len(data)}
