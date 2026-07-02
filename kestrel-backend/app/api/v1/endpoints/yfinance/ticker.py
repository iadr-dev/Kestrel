"""yfinance ticker endpoints — info, history, dividends, splits, etc."""

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_cache
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.yfinance import YFinanceProvider
from app.schemas.common import DataListResponse, DataResponse

router = APIRouter()
_yf = YFinanceProvider()


@router.get("/yf/{ticker}/info", response_model=DataResponse)
async def get_yf_info(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Company info: sector, CEO, market cap, P/E, analyst target price, etc."""
    key = build_cache_key("yf", "info", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_info(ticker)
    await cache.set(key, data, ttl=3600)
    return {"data": data}


@router.get("/yf/{ticker}/calendar", response_model=DataResponse)
async def get_yf_calendar(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Upcoming events: earnings date, dividend date, ex-dividend date, estimates."""
    key = build_cache_key("yf", "calendar", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}
    data = await _yf.get_calendar(ticker)
    await cache.set(key, data, ttl=21600)
    return {"data": data}


@router.get("/yf/{ticker}/history", response_model=DataListResponse)
async def get_yf_history(ticker: str, period: str = "1mo", interval: str = "1d") -> dict[str, Any]:
    """Historical OHLCV. Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max. Interval: 1m,5m,15m,1h,1d,1wk,1mo."""
    data = await _yf.get_history(ticker, period, interval)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/options", response_model=DataResponse)
async def get_yf_options(ticker: str) -> dict[str, Any]:
    """Options chain — expiration dates, calls, puts."""
    data = await _yf.get_options(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/dividends", response_model=DataListResponse)
async def get_yf_dividends(ticker: str) -> dict[str, Any]:
    """Dividend payment history."""
    data = await _yf.get_dividends(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/splits", response_model=DataListResponse)
async def get_yf_splits(ticker: str) -> dict[str, Any]:
    """Stock split history."""
    data = await _yf.get_splits(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/actions", response_model=DataListResponse)
async def get_yf_actions(ticker: str) -> dict[str, Any]:
    """Combined dividends + splits history."""
    data = await _yf.get_actions(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/news", response_model=DataListResponse)
async def get_yf_news(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Recent news articles with title, publisher, thumbnail."""
    key = build_cache_key("yf", "news", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached, "count": len(cached)}
    data = await _yf.get_news(ticker)
    await cache.set(key, data, ttl=1800)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/peers", response_model=DataResponse)
async def get_yf_peers(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Peer companies in the same industry."""
    key = build_cache_key("yf", "peers", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}

    if ticker.isdigit() and len(ticker) <= 5:
        # TW peers = other stocks sharing this stock's theme(s), from DuckDB.
        from app.db.duckdb.engine import get_duckdb
        db = get_duckdb()
        theme_rows = await db.aquery(
            "SELECT theme_id FROM theme_memberships WHERE stock_id = ? AND removed_at IS NULL",
            [ticker],
        )
        stock_themes = [r[0] for r in theme_rows]
        if stock_themes:
            placeholders = ",".join("?" * len(stock_themes))
            peer_rows = await db.aquery(
                f"SELECT DISTINCT stock_id FROM theme_memberships "
                f"WHERE theme_id IN ({placeholders}) AND stock_id <> ? AND removed_at IS NULL LIMIT 10",
                [*stock_themes, ticker],
            )
            peers = [r[0] for r in peer_rows]
            if peers:
                result = {"ticker": ticker, "peers": peers, "industry": stock_themes[0], "sector": "TW", "source": "theme_memberships"}
                await cache.set(key, result, ttl=86400)
                return {"data": result}

    data = await _yf.get_peers(ticker)
    await cache.set(key, data, ttl=86400)
    return {"data": data}


@router.get("/yf/{ticker}/fast-info", response_model=DataResponse)
async def get_yf_fast_info(ticker: str, cache: CacheBackend = Depends(get_cache)) -> dict[str, Any]:
    """Live US price/volume snapshot. Prefers the yfinance AsyncWebSocket one-shot
    (true real-time tick while the US market is open), falling back to REST
    fast_info (last/previous close) when the socket yields nothing — e.g. after
    hours or on WS hiccups. Cached ~10s so concurrent client polls collapse into
    one upstream fetch. Response shape matches fast_info exactly (last_price/
    previous_close/...) so callers are unchanged."""
    key = build_cache_key("yf", "fast_info", ticker=ticker)
    cached = await cache.get(key)
    if cached:
        return {"data": cached}

    data = await _yf.get_fast_info(ticker)  # REST baseline (always has prev_close etc.)

    # Overlay the live WS tick when available (keeps fast_info as the safety net).
    ws = await _yf.subscribe_realtime([ticker]) or {}
    tick = ws.get(ticker) or ws.get(_yf._resolve_ticker(ticker))
    if tick and tick.get("price"):
        data = {
            **data,
            "last_price": tick.get("price"),
            "day_high": tick.get("day_high") or data.get("day_high"),
            "day_low": tick.get("day_low") or data.get("day_low"),
            "volume": tick.get("volume") or data.get("volume"),
        }

    await cache.set(key, data, ttl=10)
    return {"data": data}


@router.get("/yf/{ticker}/isin", response_model=DataResponse)
async def get_yf_isin(ticker: str) -> dict[str, Any]:
    """Get ISIN code for a ticker."""
    isin = await _yf.get_isin(ticker)
    return {"data": {"ticker": ticker, "isin": isin}}


@router.get("/yf/{ticker}/history-metadata", response_model=DataResponse)
async def get_yf_history_metadata(ticker: str) -> dict[str, Any]:
    """Price history metadata (currency, exchange, timezone, valid ranges)."""
    data = await _yf.get_history_metadata(ticker)
    return {"data": data}


@router.get("/yf/{ticker}/capital-gains", response_model=DataListResponse)
async def get_yf_capital_gains(ticker: str) -> dict[str, Any]:
    """Capital gains distributions (for funds/ETFs)."""
    data = await _yf.get_capital_gains(ticker)
    return {"data": data, "count": len(data)}


@router.get("/yf/{ticker}/shares", response_model=DataListResponse)
async def get_yf_shares(ticker: str) -> dict[str, Any]:
    """Shares outstanding over time."""
    data = await _yf.get_shares_full(ticker)
    return {"data": data, "count": len(data)}
