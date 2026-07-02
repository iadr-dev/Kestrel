"""yfinance provider — financial statement methods."""

import asyncio
from typing import TYPE_CHECKING, Any

import yfinance as yf  # type: ignore[import-untyped]

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.providers.yfinance.provider import YFinanceProvider

logger = get_logger(__name__)


async def get_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get financial statements (income, balance sheet, cash flow)."""
    try:
        data = await asyncio.to_thread(self._fetch_financials, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_financials_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_quarterly_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get quarterly income statement, balance sheet, and cash flow."""
    try:
        return await asyncio.to_thread(self._fetch_quarterly_financials, ticker)
    except Exception as e:
        logger.warning("yfinance_quarterly_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_ttm_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get trailing twelve months (TTM) income statement and cash flow."""
    try:
        return await asyncio.to_thread(self._fetch_ttm_financials, ticker)
    except Exception as e:
        logger.warning("yfinance_ttm_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_earnings(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get annual and quarterly earnings (revenue + earnings)."""
    try:
        return await asyncio.to_thread(self._fetch_earnings, ticker)
    except Exception as e:
        logger.warning("yfinance_earnings_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_earnings_dates(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get historical earnings dates with EPS estimates vs actual."""
    try:
        data = await asyncio.to_thread(self._fetch_earnings_dates, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_earnings_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_sec_filings(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get SEC filings (10-K, 10-Q, 8-K, etc.) for US stocks."""
    try:
        return await asyncio.to_thread(self._fetch_sec_filings, ticker)
    except Exception as e:
        logger.warning("yfinance_sec_failed", ticker=ticker, error=str(e)[:100])
        return []


# --- Synchronous fetch methods ---


def _fetch_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}

    income = t.income_stmt
    if income is not None and not income.empty:
        result["income_statement"] = {
            "columns": [str(c) for c in income.columns.tolist()],
            "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in income.iterrows()},
        }

    bs = t.balance_sheet
    if bs is not None and not bs.empty:
        result["balance_sheet"] = {
            "columns": [str(c) for c in bs.columns.tolist()],
            "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in bs.iterrows()},
        }

    cf = t.cashflow
    if cf is not None and not cf.empty:
        result["cash_flow"] = {
            "columns": [str(c) for c in cf.columns.tolist()],
            "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in cf.iterrows()},
        }

    return result


def _fetch_quarterly_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    qi = t.quarterly_income_stmt
    if qi is not None and not qi.empty:
        result["quarterly_income"] = {"columns": [str(c) for c in qi.columns.tolist()], "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in qi.iterrows()}}
    qb = t.quarterly_balance_sheet
    if qb is not None and not qb.empty:
        result["quarterly_balance_sheet"] = {"columns": [str(c) for c in qb.columns.tolist()], "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in qb.iterrows()}}
    qc = t.quarterly_cashflow
    if qc is not None and not qc.empty:
        result["quarterly_cashflow"] = {"columns": [str(c) for c in qc.columns.tolist()], "data": {str(idx): [self._safe_val(v) for v in row] for idx, row in qc.iterrows()}}
    return result


def _fetch_ttm_financials(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    ttm_income = t.ttm_income_stmt
    if ttm_income is not None and not ttm_income.empty:
        result["ttm_income_stmt"] = {str(idx): self._safe_val(row.iloc[0]) for idx, row in ttm_income.iterrows()}
    ttm_cf = t.ttm_cashflow
    if ttm_cf is not None and not ttm_cf.empty:
        result["ttm_cashflow"] = {str(idx): self._safe_val(row.iloc[0]) for idx, row in ttm_cf.iterrows()}
    return result


def _fetch_earnings(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    earnings = t.earnings
    if earnings is not None and not earnings.empty:
        result["annual"] = earnings.reset_index().to_dict("records")
    qe = t.quarterly_earnings
    if qe is not None and not qe.empty:
        result["quarterly"] = qe.reset_index().to_dict("records")
    return result


def _fetch_earnings_dates(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker, "earnings_dates": []}

    ed = t.earnings_dates
    if ed is not None and not ed.empty:
        records = ed.head(12).reset_index().to_dict("records")
        result["earnings_dates"] = [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()}
            for r in records
        ]

    return result


def _fetch_sec_filings(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    filings = t.sec_filings
    if not filings:
        return []
    results = []
    for f in filings[:30]:
        item = {}
        for k, v in f.items():
            if k == "exhibits":
                item[k] = v
            elif hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = v
        results.append(item)
    return results
