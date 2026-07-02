"""yfinance provider — market, sector, industry, and calendar methods."""

import asyncio
from typing import TYPE_CHECKING, Any, cast

import yfinance as yf  # type: ignore[import-untyped]

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.providers.yfinance.provider import YFinanceProvider

logger = get_logger(__name__)


async def get_sector(self: "YFinanceProvider", sector_key: str) -> dict[str, Any]:
    """Get sector information and top companies."""
    try:
        return await asyncio.to_thread(self._fetch_sector, sector_key)
    except Exception as e:
        logger.warning("yfinance_sector_failed", sector=sector_key, error=str(e)[:100])
        return {"sector": sector_key, "error": str(e)[:100]}


async def get_industry(self: "YFinanceProvider", industry_key: str) -> dict[str, Any]:
    """Get industry information and top companies."""
    try:
        return await asyncio.to_thread(self._fetch_industry, industry_key)
    except Exception as e:
        logger.warning("yfinance_industry_failed", industry=industry_key, error=str(e)[:100])
        return {"industry": industry_key, "error": str(e)[:100]}


async def get_market_summary(self: "YFinanceProvider", market: str = "US") -> dict[str, Any]:
    """Get market summary and status. Valid markets: US, GB, ASIA, EUROPE, RATES, COMMODITIES, CURRENCIES, CRYPTOCURRENCIES."""
    try:
        return await asyncio.to_thread(self._fetch_market_summary, market)
    except Exception as e:
        logger.warning("yfinance_market_failed", market=market, error=str(e)[:100])
        return {"market": market, "error": str(e)[:100]}


async def get_earnings_calendar(self: "YFinanceProvider", start_date: str | None = None, end_date: str | None = None) -> list[dict[str, Any]]:
    """Get market-wide earnings calendar for a date range."""
    try:
        return await asyncio.to_thread(self._fetch_earnings_calendar_global, start_date, end_date)
    except Exception as e:
        logger.warning("yfinance_earnings_cal_failed", error=str(e)[:100])
        return []


async def get_splits_calendar(self: "YFinanceProvider") -> list[dict[str, Any]]:
    """Get upcoming stock splits."""
    try:
        return await asyncio.to_thread(self._fetch_splits_calendar)
    except Exception as e:
        logger.warning("yfinance_splits_cal_failed", error=str(e)[:100])
        return []


async def get_ipo_calendar(self: "YFinanceProvider") -> list[dict[str, Any]]:
    """Get upcoming IPOs."""
    try:
        return await asyncio.to_thread(self._fetch_ipo_calendar)
    except Exception as e:
        logger.warning("yfinance_ipo_cal_failed", error=str(e)[:100])
        return []


async def get_economic_events(self: "YFinanceProvider") -> list[dict[str, Any]]:
    """Get upcoming economic events."""
    try:
        return await asyncio.to_thread(self._fetch_economic_events)
    except Exception as e:
        logger.warning("yfinance_econ_events_failed", error=str(e)[:100])
        return []


# --- Synchronous fetch methods ---


def _fetch_sector(self: "YFinanceProvider", sector_key: str) -> dict[str, Any]:
    sector = yf.Sector(sector_key)
    result: dict[str, Any] = {
        "sector_key": sector_key,
        "name": getattr(sector, "name", sector_key),
        "symbol": getattr(sector, "symbol", ""),
        "overview": getattr(sector, "overview", {}),
    }
    tc = getattr(sector, "top_companies", None)
    if tc is not None and not tc.empty:
        result["top_companies"] = tc.head(15).reset_index().to_dict("records")
    te = getattr(sector, "top_etfs", None)
    if te is not None and not te.empty:
        result["top_etfs"] = te.head(10).reset_index().to_dict("records")
    tmf = getattr(sector, "top_mutual_funds", None)
    if tmf is not None and not tmf.empty:
        result["top_mutual_funds"] = tmf.head(10).reset_index().to_dict("records")
    industries = getattr(sector, "industries", None)
    if industries is not None and not industries.empty:
        result["industries"] = industries.head(20).reset_index().to_dict("records")
    return result


def _fetch_industry(self: "YFinanceProvider", industry_key: str) -> dict[str, Any]:
    ind = yf.Industry(industry_key)
    result: dict[str, Any] = {
        "industry_key": industry_key,
        "name": getattr(ind, "name", industry_key),
        "sector_key": getattr(ind, "sector_key", ""),
        "sector_name": getattr(ind, "sector_name", ""),
        "symbol": getattr(ind, "symbol", ""),
        "overview": getattr(ind, "overview", {}),
    }
    tc = getattr(ind, "top_companies", None)
    if tc is not None and not tc.empty:
        result["top_companies"] = tc.head(15).reset_index().to_dict("records")
    tgc = getattr(ind, "top_growth_companies", None)
    if tgc is not None and not tgc.empty:
        result["top_growth_companies"] = tgc.head(10).reset_index().to_dict("records")
    tpc = getattr(ind, "top_performing_companies", None)
    if tpc is not None and not tpc.empty:
        result["top_performing_companies"] = tpc.head(10).reset_index().to_dict("records")
    return result


def _fetch_market_summary(self: "YFinanceProvider", market_id: str = "US") -> dict[str, Any]:
    market = yf.Market(market_id)
    return {
        "market": market_id,
        "status": market.status or {},
        "summary": market.summary or {},
    }


def _fetch_earnings_calendar_global(self: "YFinanceProvider", start_date: str | None, end_date: str | None) -> list[dict[str, Any]]:
    from datetime import date, timedelta
    c = yf.Calendars()
    start = start_date or date.today().isoformat()
    end = end_date or (date.today() + timedelta(days=7)).isoformat()
    try:
        df = c.get_earnings_calendar(start, end)
        if df is not None and not df.empty:
            records = df.head(30).reset_index(drop=True).to_dict("records")
            return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records]
    except Exception:
        pass
    return []


def _fetch_splits_calendar(self: "YFinanceProvider") -> list[dict[str, Any]]:
    c = yf.Calendars()
    df = c.get_splits_calendar()
    if df is not None and not df.empty:
        return cast(list[dict[str, Any]], df.head(20).reset_index(drop=True).to_dict("records"))
    return []


def _fetch_ipo_calendar(self: "YFinanceProvider") -> list[dict[str, Any]]:
    c = yf.Calendars()
    df = c.get_ipo_info_calendar()
    if df is not None and not df.empty:
        return cast(list[dict[str, Any]], df.head(20).reset_index(drop=True).to_dict("records"))
    return []


def _fetch_economic_events(self: "YFinanceProvider") -> list[dict[str, Any]]:
    c = yf.Calendars()
    try:
        df = c.get_economic_events_calendar()
        if df is not None and not df.empty:
            return cast(list[dict[str, Any]], df.head(20).reset_index(drop=True).to_dict("records"))
    except Exception:
        pass
    return []
