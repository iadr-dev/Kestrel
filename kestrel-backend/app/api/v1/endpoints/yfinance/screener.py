"""yfinance screener endpoints — predefined and custom screeners + introspection."""

from typing import Any

from fastapi import APIRouter, Body, Query

from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/screen/{screen_name}", response_model=DataListResponse)
async def yf_screen(screen_name: str, size: int = 25) -> dict[str, Any]:
    """Run predefined screener: most_actives, day_gainers, day_losers, growth_technology_stocks, undervalued_large_caps, etc."""
    data = await _yf.screen(screen_name, size)
    return {"data": data, "count": len(data)}


@router.post("/yf/screen/custom", response_model=DataListResponse)
async def yf_screen_custom(request: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    """Run custom screener with filters (EquityQuery / FundQuery / ETFQuery).

    Body: {
        "query_type": "equity" | "fund" | "etf",
        "filters": [ ... ],          # flat leaves (AND-combined) OR a single nested group
        "sort_field": "intradaymarketcap",
        "sort_asc": false,
        "size": 25,                  # clamped to yfinance max 250
        "offset": 0
    }

    A filter is either a LEAF `{"op": "eq|is-in|btwn|gt|lt|gte|lte", "field", "value"}`
    or a GROUP `{"op": "and"|"or", "filters": [<filter>, ...]}` (groups nest arbitrarily).
    """
    data = await _yf.screen_custom(
        query_type=request.get("query_type", "equity"),
        filters=request.get("filters", []),
        sort_field=request.get("sort_field", "intradaymarketcap"),
        sort_asc=request.get("sort_asc", False),
        size=request.get("size", 25),
        offset=request.get("offset", 0),
        region=request.get("region", "us"),
    )
    return {"data": data, "count": len(data)}


@router.get("/yf/screener/fields", response_model=DataResponse)
async def yf_screener_fields(type: str = Query("equity", pattern="^(equity|fund|etf)$")) -> dict[str, Any]:
    """valid_fields for a query type, grouped by yfinance's own categories.

    Drives the US custom-filter sidebar (so it mirrors yfinance exactly instead of
    hand-listing fields). equity=90 fields/12 cats, etf=37/10, fund=9/2."""
    data = await _yf.get_screener_fields(type)
    return {"data": {"query_type": type, "fields": data}}


@router.get("/yf/screener/values", response_model=DataResponse)
async def yf_screener_values(type: str = Query("equity", pattern="^(equity|fund|etf)$")) -> dict[str, Any]:
    """valid_values (restricted enums: region/sector/industry/exchange/categoryname/…)
    for eq/is-in dropdowns in the custom-filter sidebar."""
    data = await _yf.get_screener_values(type)
    return {"data": {"query_type": type, "values": data}}


@router.get("/yf/screener/presets", response_model=DataListResponse)
async def yf_screener_presets() -> dict[str, Any]:
    """Predefined yfinance screen names + inferred query type (data-driven preset gallery)."""
    data = await _yf.list_predefined_screens()
    return {"data": data, "count": len(data)}


@router.get("/yf/realtime/ws", response_model=DataListResponse)
async def yf_realtime_websocket(tickers: str = "") -> dict[str, Any]:
    """Get real-time price snapshot via yfinance WebSocket (US stocks).

    Tickers: comma-separated (e.g. AAPL,NVDA,TSLA).
    """
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return {"data": {}, "count": 0}
    data = await _yf.subscribe_realtime(ticker_list)
    return {"data": data, "count": len(data)}
