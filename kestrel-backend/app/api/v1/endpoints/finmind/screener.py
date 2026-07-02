from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_screener_service
from app.schemas.common import DataListResponse
from app.services.data.screener_service import ScreenerService

router = APIRouter(prefix="/screener", tags=["Screener"])


class ScreenRequest(BaseModel):
    screen_type: str
    trade_date: date
    # Markets: tw / tw_etf → FinMind+DuckDB (we screen); us / us_etf → yfinance (Yahoo
    # screens). Legacy "etf" == US ETF (back-compat, normalized to us_etf below).
    market: str = "tw"
    mode: str = "afterhours"  # realtime, afterhours
    params: dict[str, Any] | None = None


# Markets routed to the yfinance (US) screener vs the DuckDB (TW) screener. Keying
# purely on `market` (not the screen_type prefix) so a prefix mismatch can never
# cross-query the wrong data source.
_US_MARKETS = {"us", "us_etf", "etf"}  # "etf" = legacy alias for us_etf


@router.post("/run", response_model=DataListResponse)
async def run_screen(
    request: ScreenRequest,
    service: ScreenerService = Depends(get_screener_service),
) -> dict[str, Any]:
    if request.market in _US_MARKETS:
        data = await _run_yfinance_screen(request.screen_type)
    else:
        # tw / tw_etf → our DuckDB screens.
        data = await service.run_screen(request.screen_type, request.trade_date, request.params)
    return {"data": data, "count": len(data)}


async def _run_yfinance_screen(screen_type: str) -> list[dict[str, Any]]:
    """Run US/ETF screener via yfinance predefined screeners."""
    import asyncio

    SCREEN_MAP = {
        "us_momentum": "most_actives",
        "us_day_gainers": "day_gainers",
        "us_day_losers": "day_losers",
        "us_growth_tech": "growth_technology_stocks",
        "us_undervalued_large": "undervalued_large_caps",
        "us_undervalued_growth": "undervalued_growth_stocks",
        "us_shorted": "most_shorted_stocks",
        "us_small_cap": "small_cap_gainers",
        "us_earnings_beat": "day_gainers",
        "us_high_volume": "most_actives",
        "etf_top": "top_etfs_us",
        "etf_performing": "top_performing_etfs",
        "etf_tech": "technology_etfs",
        "etf_bond": "bond_etfs",
        "etf_high_dividend": "top_etfs_us",
        "etf_volume_spike": "top_etfs_us",
        "etf_volume_surge": "top_etfs_us",
        "etf_premium": "top_performing_etfs",
    }

    predefined = SCREEN_MAP.get(screen_type, "most_actives")

    def _screen() -> list[dict[str, Any]]:
        import yfinance as yf  # type: ignore[import-untyped]
        response = yf.screen(predefined, count=30)
        quotes = response.get("quotes", [])
        results: list[dict[str, Any]] = []
        for q in quotes[:30]:
            results.append({
                "stock_id": q.get("symbol", ""),
                "stock_name": q.get("shortName") or q.get("longName", ""),
                "close": q.get("regularMarketPrice"),
                "spread": q.get("regularMarketChange"),
                "volume": q.get("regularMarketVolume"),
            })
        return results

    return await asyncio.to_thread(_screen)


@router.get("/presets", response_model=DataListResponse)
async def get_presets(
    service: ScreenerService = Depends(get_screener_service),
) -> dict[str, Any]:
    presets = service.get_presets()
    return {"data": presets, "count": len(presets)}


@router.get("/tw/factors", response_model=DataListResponse)
async def get_tw_factor_catalog(
    service: ScreenerService = Depends(get_screener_service),
) -> dict[str, Any]:
    """Categorized, bilingual TW screen catalog (technical / momentum / chip) — the TW
    counterpart to yfinance's valid_fields, used to render the TW custom-filter sidebar."""
    catalog = service.get_factor_catalog()
    return {"data": catalog, "count": len(catalog)}


@router.get("/backtest", response_model=DataListResponse)
async def get_backtest(
    strategy: str = Query(..., description="ma_golden_cross | kd_low_cross | breakout_20d | inst_buy_3d"),
) -> dict[str, Any]:
    """Get backtest results for a strategy (top 5 stocks by win rate).

    Uses DuckDB pre-computed data when available, falls back to live FinMind fetch.
    """
    from app.db.duckdb.engine import get_duckdb
    from app.services.compute.backtest_service import STRATEGIES, compute_backtest

    if strategy not in STRATEGIES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}. Available: {list(STRATEGIES.keys())}")

    # Try DuckDB first (pre-computed, instant)
    db = get_duckdb()
    if db.get_stock_count() > 0:
        try:
            if strategy == "ma_golden_cross":
                data = db.compute_backtest_ma_cross()
            elif strategy == "breakout_20d":
                data = db.compute_backtest_breakout()
            else:
                # Other strategies: fall back to live computation
                data = await compute_backtest(strategy)

            if data:
                return {"data": data, "count": len(data), "strategy": STRATEGIES[strategy], "source": "duckdb"}
        except Exception:
            pass

    # Fallback: live computation from FinMind
    data = await compute_backtest(strategy)
    return {
        "data": data,
        "count": len(data),
        "strategy": STRATEGIES[strategy],
        "source": "live",
    }


@router.get("/backtest/strategies", response_model=DataListResponse)
async def get_strategies() -> dict[str, Any]:
    """List all available backtest strategies."""
    from app.services.compute.backtest_service import STRATEGIES
    return {
        "data": [{"id": k, **v} for k, v in STRATEGIES.items()],
        "count": len(STRATEGIES),
    }
