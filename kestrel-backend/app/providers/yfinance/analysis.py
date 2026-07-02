"""yfinance provider — analysis methods (recommendations, insiders, holders, estimates)."""

import asyncio
from typing import TYPE_CHECKING, Any, cast

import yfinance as yf  # type: ignore[import-untyped]

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.providers.yfinance.provider import YFinanceProvider

logger = get_logger(__name__)


async def get_recommendations(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get analyst recommendations + upgrades/downgrades."""
    try:
        data = await asyncio.to_thread(self._fetch_recommendations, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_recommendations_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_recommendations_summary(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get aggregated recommendations summary (buy/hold/sell counts by period)."""
    try:
        return await asyncio.to_thread(self._fetch_recommendations_summary, ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_earnings_history(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get historical EPS actual vs estimate (surprises)."""
    try:
        return await asyncio.to_thread(self._fetch_earnings_history, ticker)
    except Exception:
        return []


async def get_eps_revisions(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get analyst EPS revision trends (up/down revisions)."""
    try:
        return await asyncio.to_thread(self._fetch_eps_revisions, ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_growth_estimates(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get growth rate estimates (current qtr, next qtr, current year, next year, 5yr)."""
    try:
        return await asyncio.to_thread(self._fetch_growth_estimates, ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_holders(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get institutional + mutual fund holders."""
    try:
        data = await asyncio.to_thread(self._fetch_holders, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_holders_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_insider_transactions(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get recent insider buy/sell transactions."""
    try:
        data = await asyncio.to_thread(self._fetch_insiders, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_insiders_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_insider_purchases(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get insider purchase summary (aggregated buy activity)."""
    try:
        return await asyncio.to_thread(self._fetch_insider_purchases, ticker)
    except Exception:
        return []


async def get_insider_roster(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get insider roster with positions and latest transactions."""
    try:
        return await asyncio.to_thread(self._fetch_insider_roster, ticker)
    except Exception:
        return []


async def get_major_holders(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get major holders breakdown (% insiders, % institutions)."""
    try:
        return await asyncio.to_thread(self._fetch_major_holders, ticker)
    except Exception as e:
        logger.warning("yfinance_major_holders_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_shares_full(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    """Get shares outstanding over time."""
    try:
        return await asyncio.to_thread(self._fetch_shares_full, ticker)
    except Exception as e:
        logger.warning("yfinance_shares_failed", ticker=ticker, error=str(e)[:100])
        return []


async def get_analyst_price_targets(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get detailed analyst price target breakdown (current, low, high, mean, median)."""
    try:
        return await asyncio.to_thread(self._fetch_analyst_price_targets, ticker)
    except Exception as e:
        logger.warning("yfinance_targets_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_earnings_estimate(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get earnings/revenue estimates and EPS trend."""
    try:
        return await asyncio.to_thread(self._fetch_earnings_estimate, ticker)
    except Exception as e:
        logger.warning("yfinance_estimate_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_sustainability(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get ESG sustainability scores."""
    try:
        return await asyncio.to_thread(self._fetch_sustainability, ticker)
    except Exception as e:
        logger.warning("yfinance_sustainability_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "error": str(e)[:100]}


async def get_peers(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get peer companies in the same industry."""
    try:
        data = await asyncio.to_thread(self._fetch_peers, ticker)
        return data
    except Exception as e:
        logger.warning("yfinance_peers_failed", ticker=ticker, error=str(e)[:100])
        return {"ticker": ticker, "peers": [], "error": str(e)[:100]}


async def get_funds_data(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    """Get ETF/fund specific data (holdings, sector weights, bond ratings)."""
    try:
        return await asyncio.to_thread(self._fetch_funds_data, ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)[:100]}


# --- Synchronous fetch methods ---


def _fetch_recommendations(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker, "recommendations": [], "upgrades_downgrades": []}

    recs = t.recommendations
    if recs is not None and not recs.empty:
        result["recommendations"] = recs.tail(20).to_dict("records")

    upgrades = t.upgrades_downgrades
    if upgrades is not None and not upgrades.empty:
        result["upgrades_downgrades"] = upgrades.tail(20).to_dict("records")

    return result


def _fetch_recommendations_summary(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.recommendations_summary
    if df is None or df.empty:
        return {"ticker": ticker}
    return {"ticker": ticker, "summary": df.to_dict()}


def _fetch_earnings_history(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.earnings_history
    if df is None or df.empty:
        return []
    return cast(list[dict[str, Any]], df.reset_index(drop=True).to_dict("records"))


def _fetch_eps_revisions(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.eps_revisions
    if df is None or df.empty:
        return {"ticker": ticker}
    return {"ticker": ticker, "revisions": df.to_dict()}


def _fetch_growth_estimates(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.growth_estimates
    if df is None or df.empty:
        return {"ticker": ticker}
    return {"ticker": ticker, "estimates": df.to_dict()}


def _fetch_holders(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker, "institutional": [], "mutual_fund": []}

    inst = t.institutional_holders
    if inst is not None and not inst.empty:
        result["institutional"] = inst.head(10).to_dict("records")

    mf = t.mutualfund_holders
    if mf is not None and not mf.empty:
        result["mutual_fund"] = mf.head(10).to_dict("records")

    return result


def _fetch_insiders(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker, "transactions": []}

    txns = t.insider_transactions
    if txns is not None and not txns.empty:
        result["transactions"] = txns.head(20).to_dict("records")

    return result


def _fetch_insider_purchases(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.insider_purchases
    if df is None or df.empty:
        return []
    return cast(list[dict[str, Any]], df.to_dict("records"))


def _fetch_insider_roster(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    df = t.insider_roster_holders
    if df is None or df.empty:
        return []
    records = df.head(15).to_dict("records")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records]


def _fetch_major_holders(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    mh = t.major_holders
    if mh is not None and not mh.empty:
        result["breakdown"] = mh.to_dict()
    return result


def _fetch_shares_full(self: "YFinanceProvider", ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    shares = t.get_shares_full(start="2020-01-01")
    if shares is None or shares.empty:
        return []
    records = shares.reset_index().to_dict("records")
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else self._safe_val(v)) for k, v in r.items()} for r in records[-20:]]


def _fetch_analyst_price_targets(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    apt = t.analyst_price_targets
    if apt is not None and isinstance(apt, dict):
        result.update(apt)
    elif apt is not None and hasattr(apt, "to_dict"):
        result.update(apt.to_dict())
    return result


def _fetch_earnings_estimate(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    re_est = t.revenue_estimate
    if re_est is not None and not re_est.empty:
        result["revenue_estimate"] = re_est.to_dict()
    ee = t.earnings_estimate
    if ee is not None and not ee.empty:
        result["earnings_estimate"] = ee.to_dict()
    eps = t.eps_trend
    if eps is not None and not eps.empty:
        result["eps_trend"] = eps.to_dict()
    return result


def _fetch_sustainability(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    result: dict[str, Any] = {"ticker": ticker}
    sus = t.sustainability
    if sus is not None and not sus.empty:
        result["scores"] = sus.to_dict()
    return result


def _fetch_peers(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    info = t.info or {}
    industry_key = info.get("industryKey", "")

    result: dict[str, Any] = {
        "ticker": ticker,
        "industry": info.get("industry", ""),
        "sector": info.get("sector", ""),
        "peers": [],
    }

    if industry_key:
        try:
            ind = yf.Industry(industry_key)
            tc = ind.top_companies
            if tc is not None and not tc.empty:
                resolved = self._resolve_ticker(ticker)
                peers = [sym for sym in tc.head(12).index if sym != resolved and sym != ticker]
                result["peers"] = peers[:10]
        except Exception:
            pass

    return result


def _fetch_funds_data(self: "YFinanceProvider", ticker: str) -> dict[str, Any]:
    t = yf.Ticker(self._resolve_ticker(ticker))
    fd = t.funds_data
    if fd is None:
        return {"ticker": ticker}
    result: dict[str, Any] = {"ticker": ticker}
    if hasattr(fd, "top_holdings") and fd.top_holdings is not None:
        result["top_holdings"] = fd.top_holdings.head(10).to_dict("records") if not fd.top_holdings.empty else []
    if hasattr(fd, "sector_weightings") and fd.sector_weightings:
        result["sector_weightings"] = fd.sector_weightings
    if hasattr(fd, "bond_ratings") and fd.bond_ratings:
        result["bond_ratings"] = fd.bond_ratings
    if hasattr(fd, "fund_overview") and fd.fund_overview:
        result["fund_overview"] = fd.fund_overview
    return result
