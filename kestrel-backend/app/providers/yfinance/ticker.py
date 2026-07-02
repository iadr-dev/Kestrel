"""yfinance provider — ticker data methods (info, history, dividends, splits, etc.)."""

import asyncio
from typing import TYPE_CHECKING, Any

import yfinance as yf  # type: ignore[import-untyped]

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.providers.yfinance.provider import YFinanceProvider

logger = get_logger(__name__)


async def get_info(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get comprehensive company info (300+ fields)."""
    try:
        data = await asyncio.to_thread(self._fetch_info, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_info_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_calendar(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get upcoming events: earnings date, dividend date, ex-dividend date."""
    try:
        data = await asyncio.to_thread(self._fetch_calendar, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_calendar_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_news(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get recent news articles with thumbnails."""
    try:
        data = await asyncio.to_thread(self._fetch_news, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_news_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_history(self: "YFinanceProvider", ticker: str, period: str = "1mo", interval: str = "1d") -> list[dict[str, Any]]:
    """Get historical OHLCV data. Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max. Interval: 1m,5m,15m,1h,1d,1wk,1mo."""
    try:
        return await asyncio.to_thread(self._fetch_history, ticker, period, interval)
    except Exception as e:
        logger.warning("yfinance_history_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_options(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get options chain — available expiration dates and current chain."""
    try:
        return await asyncio.to_thread(self._fetch_options, ticker)
    except Exception as e:
        logger.warning("yfinance_options_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_dividends(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get dividend history."""
    try:
        return await asyncio.to_thread(self._fetch_dividends, ticker)
    except Exception as e:
        logger.warning("yfinance_dividends_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_splits(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get stock split history."""
    try:
        return await asyncio.to_thread(self._fetch_splits, ticker)
    except Exception as e:
        logger.warning("yfinance_splits_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_actions(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get combined dividends + splits history."""
    try:
        return await asyncio.to_thread(self._fetch_actions, ticker)
    except Exception as e:
        logger.warning("yfinance_actions_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_fast_info(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get lightweight price/volume snapshot (faster than full info)."""
    try:
        return await asyncio.to_thread(self._fetch_fast_info, ticker)
    except Exception as e:
        logger.warning("yfinance_fast_info_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_isin(self: "YFinanceProvider", ticker: str) -> str | None:
    """Get ISIN code for a ticker."""
    try:
        return await asyncio.to_thread(self._fetch_isin, ticker)
    except Exception:
        return None


async def get_history_metadata(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get metadata about price history (currency, exchange, timezone, valid ranges)."""
    try:
        return await asyncio.to_thread(self._fetch_history_metadata, ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_capital_gains(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get capital gains distributions (primarily for funds/ETFs)."""
    try:
        return await asyncio.to_thread(self._fetch_capital_gains, ticker)
    except Exception:
        return []


# --- Synchronous fetch methods ---


def _fetch_info(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    info = t.info or {}
    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName", ""),
        # quoteType distinguishes EQUITY / ETF / MUTUALFUND / INDEX — lets the
        # frontend refine a US ticker to the right asset kind (SPY vs AAPL).
        "quote_type": info.get("quoteType"),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "country": info.get("country", ""),
        "website": info.get("website", ""),
        "employees": info.get("fullTimeEmployees"),
        "description": info.get("longBusinessSummary", "")[:500],
        "ceo": next((o.get("name") for o in info.get("companyOfficers", []) if "CEO" in (o.get("title") or "")), None),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "target_mean_price": info.get("targetMeanPrice"),
        "target_high_price": info.get("targetHighPrice"),
        "target_low_price": info.get("targetLowPrice"),
        "recommendation": info.get("recommendationKey"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "beta": info.get("beta"),
        "revenue": info.get("totalRevenue"),
        "gross_profit": info.get("grossProfits"),
        "ebitda": info.get("ebitda"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
    }


def _fetch_calendar(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    cal = t.calendar
    result: dict[str, Any] = {"ticker": ticker}
    if isinstance(cal, dict):
        for k, v in cal.items():
            if hasattr(v, "isoformat"):
                result[k] = v.isoformat()
            elif isinstance(v, list):
                result[k] = [x.isoformat() if hasattr(x, "isoformat") else str(x) for x in v]
            else:
                result[k] = v
    return result


def _fetch_news(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    news = t.news or []
    return [
        {
            "title": n.get("title", ""),
            "publisher": n.get("publisher", ""),
            "link": n.get("link", ""),
            "published": n.get("providerPublishTime", ""),
            "thumbnail": (n.get("thumbnail", {}) or {}).get("resolutions", [{}])[0].get("url") if n.get("thumbnail") else None,
        }
        for n in news[:20]
    ]


def _fetch_history(self: "YFinanceProvider", ticker: str, period: str, interval: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.history(period=period, interval=interval)
    if df is None or df.empty:
        return []
    records = df.reset_index().to_dict("records")
    return [
        {k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()}
        for r in records
    ]


def _fetch_options(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    expirations = t.options
    result: dict[str, Any] = {"ticker": ticker, "expirations": list(expirations) if expirations else []}
    if expirations:
        chain = t.option_chain(expirations[0])
        if chain.calls is not None and not chain.calls.empty:
            result["calls"] = chain.calls.head(10).to_dict("records")
        if chain.puts is not None and not chain.puts.empty:
            result["puts"] = chain.puts.head(10).to_dict("records")
    return result


def _fetch_dividends(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    divs = t.dividends
    if divs is None or divs.empty:
        return []
    records = divs.reset_index().to_dict("records")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records[-20:]]


def _fetch_splits(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    splits = t.splits
    if splits is None or splits.empty:
        return []
    records = splits.reset_index().to_dict("records")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records]


def _fetch_actions(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    actions = t.actions
    if actions is None or actions.empty:
        return []
    records = actions.reset_index().to_dict("records")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records[-30:]]


def _fetch_fast_info(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    fi = t.fast_info
    return {
        "ticker": ticker,
        "last_price": fi.get("lastPrice") if hasattr(fi, "get") else getattr(fi, "last_price", None),
        "previous_close": fi.get("previousClose") if hasattr(fi, "get") else getattr(fi, "previous_close", None),
        "open": fi.get("open") if hasattr(fi, "get") else getattr(fi, "open", None),
        "day_high": fi.get("dayHigh") if hasattr(fi, "get") else getattr(fi, "day_high", None),
        "day_low": fi.get("dayLow") if hasattr(fi, "get") else getattr(fi, "day_low", None),
        "volume": fi.get("lastVolume") if hasattr(fi, "get") else getattr(fi, "last_volume", None),
        "market_cap": fi.get("marketCap") if hasattr(fi, "get") else getattr(fi, "market_cap", None),
        "fifty_day_average": fi.get("fiftyDayAverage") if hasattr(fi, "get") else getattr(fi, "fifty_day_average", None),
        "two_hundred_day_average": fi.get("twoHundredDayAverage") if hasattr(fi, "get") else getattr(fi, "two_hundred_day_average", None),
    }


def _fetch_isin(self: "YFinanceProvider", ticker: str) -> str | None:
    t = yf.Ticker(self._resolve_ticker(ticker))
    return t.isin if hasattr(t, "isin") else None


def _fetch_history_metadata(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    t.history(period="1d")
    md = t.history_metadata if hasattr(t, "history_metadata") else {}
    result: dict[str, Any] = {"ticker": ticker}
    if isinstance(md, dict):
        result.update({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in md.items() if not callable(v)})
    return result


def _fetch_capital_gains(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    cg = t.capital_gains if hasattr(t, "capital_gains") else None
    if cg is None or (hasattr(cg, "empty") and cg.empty):
        return []
    if hasattr(cg, "reset_index"):
        records = cg.reset_index().to_dict("records")
        return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records]
    return []
