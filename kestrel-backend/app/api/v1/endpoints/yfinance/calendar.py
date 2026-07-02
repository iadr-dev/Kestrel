"""yfinance calendar endpoints — earnings, splits, IPO, economic events."""

from typing import Any

from fastapi import APIRouter

from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/calendar/earnings", response_model=DataListResponse)
async def get_yf_earnings_calendar_global(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    """Market-wide earnings calendar for a date range (default: next 7 days)."""
    data = await _yf.get_earnings_calendar(start_date, end_date)
    return {"data": data, "count": len(data)}


@router.get("/yf/calendar/splits", response_model=DataListResponse)
async def get_yf_splits_calendar() -> dict[str, Any]:
    """Upcoming stock splits."""
    data = await _yf.get_splits_calendar()
    return {"data": data, "count": len(data)}


@router.get("/yf/calendar/ipo", response_model=DataListResponse)
async def get_yf_ipo_calendar() -> dict[str, Any]:
    """Upcoming IPOs."""
    data = await _yf.get_ipo_calendar()
    return {"data": data, "count": len(data)}


@router.get("/yf/calendar/economic", response_model=DataListResponse)
async def get_yf_economic_events() -> dict[str, Any]:
    """Upcoming economic events."""
    data = await _yf.get_economic_events()
    return {"data": data, "count": len(data)}
