"""yfinance provider — search, screener, and real-time WebSocket methods."""

import asyncio
from typing import TYPE_CHECKING, Any, cast

import yfinance as yf  # type: ignore[import-untyped]

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.providers.yfinance.provider import YFinanceProvider

logger = get_logger(__name__)


async def search(self: "YFinanceProvider", query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search for tickers by keyword."""
    try:
        return await asyncio.to_thread(self._fetch_search, query, max_results)
    except Exception as e:
        logger.warning("yfinance_search_failed", query=query, error=str(e)[:100])
        return []


async def search_news(self: "YFinanceProvider", query: str) -> list[dict[str, Any]]:
    """Search for news by keyword."""
    try:
        return await asyncio.to_thread(self._fetch_search_news, query)
    except Exception as e:
        logger.warning("yfinance_search_news_failed", query=query, error=str(e)[:100])
        return []


async def lookup(self: "YFinanceProvider", query: str, asset_type: str = "stock") -> list[dict[str, Any]]:
    """Lookup tickers by type: stock, etf, mutualfund, cryptocurrency, currency, future, index."""
    try:
        return await asyncio.to_thread(self._fetch_lookup, query, asset_type)
    except Exception as e:
        logger.warning("yfinance_lookup_failed", query=query, error=str(e)[:100])
        return []


async def screen(self: "YFinanceProvider", screen_name: str, size: int = 25) -> list[dict[str, Any]]:
    """Run a predefined screener (most_actives, day_gainers, day_losers, etc.)."""
    try:
        return await asyncio.to_thread(self._fetch_screen, screen_name, size)
    except Exception as e:
        logger.warning("yfinance_screen_failed", screen=screen_name, error=str(e)[:100])
        return []


async def screen_custom(self: "YFinanceProvider", query_type: str, filters: list[dict[str, Any]], sort_field: str = "intradaymarketcap", sort_asc: bool = False, size: int = 25, offset: int = 0, region: str | None = "us") -> list[dict[str, Any]]:
    """Run custom screener with EquityQuery/FundQuery/ETFQuery filters.

    `filters` may be a flat list of leaves (AND-combined, legacy shape) or a single
    nested group `[{"op": "and"|"or", "filters": [...]}]` — see _build_query.
    `region` default-scopes equity/etf queries (yfinance's screener is global);
    pass None to disable, or include your own region filter."""
    try:
        return await asyncio.to_thread(self._fetch_screen_custom, query_type, filters, sort_field, sort_asc, size, offset, region)
    except Exception as e:
        logger.warning("yfinance_custom_screen_failed", error=str(e)[:100])
        return []


# --- Screener introspection (drives the frontend's generated US filter UI) -----
# These mirror yfinance's own EquityQuery/FundQuery/ETFQuery metadata exactly, so the
# UI never hand-lists fields: valid_fields (operands by category), valid_values
# (restricted enums like region/sector/exchange), and the predefined screen catalog.

def _query_class(query_type: str) -> Any:
    from yfinance import EquityQuery, ETFQuery, FundQuery
    return {"equity": EquityQuery, "fund": FundQuery, "etf": ETFQuery}.get(query_type, EquityQuery)


async def get_screener_fields(self: "YFinanceProvider", query_type: str = "equity") -> dict[str, list[str]]:
    """valid_fields for a query type, grouped by category (e.g. price, valuation…)."""
    def _fetch() -> dict[str, list[str]]:
        from yfinance.const import (  # type: ignore[import-untyped]
            EQUITY_SCREENER_FIELDS,
            ETF_SCREENER_FIELDS,
            FUND_SCREENER_FIELDS,
        )
        src = {"equity": EQUITY_SCREENER_FIELDS, "fund": FUND_SCREENER_FIELDS, "etf": ETF_SCREENER_FIELDS}.get(query_type, EQUITY_SCREENER_FIELDS)
        return {cat: sorted(fields) for cat, fields in src.items()}
    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.warning("yfinance_screener_fields_failed", query_type=query_type, error=str(e)[:100])
        return {}


async def get_screener_values(self: "YFinanceProvider", query_type: str = "equity") -> dict[str, Any]:
    """valid_values for a query type — restricted enums (region/exchange/sector/…)."""
    def _fetch() -> dict[str, Any]:
        from yfinance.const import (
            EQUITY_SCREENER_EQ_MAP,
            ETF_SCREENER_EQ_MAP,
            FUND_SCREENER_EQ_MAP,
        )
        src = {"equity": EQUITY_SCREENER_EQ_MAP, "fund": FUND_SCREENER_EQ_MAP, "etf": ETF_SCREENER_EQ_MAP}.get(query_type, EQUITY_SCREENER_EQ_MAP)
        # Values may be sets (unordered) → sort for a stable response. Exchange is a
        # region→list map; pass it through as-is.
        out: dict[str, Any] = {}
        for field, vals in src.items():
            if isinstance(vals, dict):
                out[field] = {k: sorted(v) if isinstance(v, (set, list, tuple)) else v for k, v in vals.items()}
            elif isinstance(vals, (set, list, tuple)):
                out[field] = sorted(vals)
            else:
                out[field] = vals
        return out
    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.warning("yfinance_screener_values_failed", query_type=query_type, error=str(e)[:100])
        return {}


async def list_predefined_screens(self: "YFinanceProvider") -> list[dict[str, str]]:
    """Predefined screen names + inferred query type (equity/fund/etf)."""
    def _fetch() -> list[dict[str, str]]:
        predefined = getattr(yf, "PREDEFINED_SCREENER_QUERIES", {}) or {}
        result: list[dict[str, str]] = []
        for name, body in predefined.items():
            qcls = type(body.get("query")).__name__ if isinstance(body, dict) else type(body).__name__
            qtype = {"EquityQuery": "equity", "FundQuery": "fund", "ETFQuery": "etf"}.get(qcls, "equity")
            result.append({"name": name, "query_type": qtype})
        return result
    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.warning("yfinance_predefined_list_failed", error=str(e)[:100])
        return []


async def subscribe_realtime(self: "YFinanceProvider", tickers: list[str], on_message: Any = None) -> dict[str, Any]:
    """Subscribe to real-time price updates via yfinance AsyncWebSocket."""
    try:
        return await self._fetch_realtime_ws(tickers)
    except Exception as e:
        logger.warning("yfinance_ws_failed", error=str(e)[:100])
        return {}


async def _fetch_realtime_ws(self: "YFinanceProvider", tickers: list[str]) -> dict[str, Any]:
    """Get latest real-time prices using yfinance AsyncWebSocket (one-shot snapshot)."""
    resolved = [self._resolve_ticker(t) for t in tickers]
    results: dict[str, Any] = {}
    received_count = 0

    def on_message(msg: dict[str, Any]) -> None:
        nonlocal received_count
        symbol = msg.get("id", "")
        results[symbol] = {
            "price": msg.get("price"),
            "volume": msg.get("dayVolume"),
            "change": msg.get("change"),
            "change_pct": msg.get("changePercent"),
            "time": msg.get("time"),
            "bid": msg.get("bid"),
            "ask": msg.get("ask"),
            "day_high": msg.get("dayHigh"),
            "day_low": msg.get("dayLow"),
        }
        received_count += 1

    try:
        ws = yf.AsyncWebSocket()
        await ws.subscribe(resolved)

        listen_task = asyncio.create_task(ws.listen(on_message))
        # Early-exit: stop as soon as every subscribed ticker has reported a tick,
        # capped at a 2s ceiling. Avoids a fixed 3s block on every call (most ticks
        # arrive in <500ms while the market is open; after hours none arrive and we
        # hit the ceiling, then fall back to fast_info upstream).
        for _ in range(20):
            await asyncio.sleep(0.1)
            if received_count >= len(resolved):
                break
        listen_task.cancel()
        await ws.close()
    except asyncio.CancelledError:
        pass
    except Exception:
        for t in tickers:
            try:
                fi = await self.get_fast_info(t)
                results[t] = fi
            except Exception:
                pass

    return results


# --- Synchronous fetch methods ---


def _fetch_search(self: "YFinanceProvider", query: str, max_results: int) -> list[dict[str, Any]]:
    results = yf.Search(query)
    quotes = results.quotes if hasattr(results, "quotes") else []
    return [
        {"symbol": q.get("symbol", ""), "name": q.get("shortname") or q.get("longname", ""), "exchange": q.get("exchange", ""), "type": q.get("quoteType", ""), "sector": q.get("sector", ""), "industry": q.get("industry", "")}
        for q in quotes[:max_results]
    ]


def _fetch_search_news(self: "YFinanceProvider", query: str) -> list[dict[str, Any]]:
    results = yf.Search(query)
    news = results.news if hasattr(results, "news") else []
    return [{"title": n.get("title", ""), "publisher": n.get("publisher", ""), "link": n.get("link", ""), "published": n.get("providerPublishTime", "")} for n in news[:15]]


def _fetch_lookup(self: "YFinanceProvider", query: str, asset_type: str) -> list[dict[str, Any]]:
    lookup = yf.Lookup(query)
    method = getattr(lookup, f"get_{asset_type}", None) or getattr(lookup, asset_type, None)
    if callable(method):
        df = method()
    else:
        df = method
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    if hasattr(df, "to_dict"):
        return cast(list[dict[str, Any]], df.head(20).reset_index(drop=True).to_dict("records"))
    return []


_GROUP_OPS = {"and", "or"}
_SCREEN_MAX = 250  # yfinance hard cap for size/count


def _build_query(query_class: Any, node: dict[str, Any]) -> Any:
    """Recursively build an EquityQuery/FundQuery/ETFQuery from a filter node.

    A node is either:
      - a GROUP:  {"op": "and"|"or", "filters": [<node>, ...]}
      - a LEAF:   {"op": "eq|is-in|btwn|gt|lt|gte|lte", "field": str, "value": ...}
    Mirrors yfinance's operand shapes: is-in → [field, *values]; btwn → [field, lo, hi];
    every other value op → [field, value]."""
    op = node.get("op", "gt")
    if op in _GROUP_OPS:
        children = [_build_query(query_class, c) for c in node.get("filters", []) if c]
        children = [c for c in children if c is not None]
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        return query_class(op, children)

    field = node.get("field", "")
    value = node.get("value", 0)
    if op == "is-in":
        vals = value if isinstance(value, list) else [value]
        return query_class(op, [field, *vals])
    if op == "btwn":
        lo, hi = (value[0], value[1]) if isinstance(value, list) else (value, value)
        return query_class(op, [field, lo, hi])
    # eq / gt / lt / gte / lte — two-operand form.
    return query_class(op, [field, value])


def _map_screen_quote(q: dict[str, Any]) -> dict[str, Any]:
    """Map a yfinance screener quote to our row shape. Carries the extra fundamental
    columns the US 'lens' column-sets render (PE/PB/ROE/margins/52wk/sector/…)."""
    return {
        "symbol": q.get("symbol", ""),
        "name": q.get("shortName") or q.get("longName", ""),
        "price": q.get("regularMarketPrice"),
        "change": q.get("regularMarketChange"),
        "change_pct": q.get("regularMarketChangePercent"),
        "volume": q.get("regularMarketVolume"),
        "market_cap": q.get("marketCap"),
        "pe": q.get("trailingPE"),
        "forward_pe": q.get("forwardPE"),
        "price_to_book": q.get("priceToBook"),
        "dividend_yield": q.get("dividendYield") or q.get("trailingAnnualDividendYield"),
        "eps": q.get("epsTrailingTwelveMonths"),
        "fifty_two_week_change_pct": q.get("fiftyTwoWeekChangePercent"),
        "sector": q.get("sector"),
        "exchange": q.get("fullExchangeName") or q.get("exchange"),
        # ETF-relevant fields (present on fund/ETF quotes).
        "net_assets": q.get("netAssets"),
        "ytd_return": q.get("ytdReturn"),
    }


def _fetch_screen(self: "YFinanceProvider", screen_name: str, size: int) -> list[dict[str, Any]]:
    size = max(1, min(size, _SCREEN_MAX))
    response = yf.screen(screen_name, count=size)
    quotes = response.get("quotes", [])
    return [_map_screen_quote(q) for q in quotes[:size]]


def _has_field(node: dict[str, Any], field: str) -> bool:
    """True if a region/sector/etc. field appears anywhere in the (possibly nested) filter tree."""
    if node.get("op") in _GROUP_OPS:
        return any(_has_field(c, field) for c in node.get("filters", []) if isinstance(c, dict))
    return node.get("field") == field


def _fetch_screen_custom(self: "YFinanceProvider", query_type: str, filters: list[dict[str, Any]], sort_field: str, sort_asc: bool, size: int, offset: int = 0, region: str | None = "us") -> list[dict[str, Any]]:
    query_class = _query_class(query_type)
    size = max(1, min(size, _SCREEN_MAX))
    offset = max(0, offset)

    # Accept either a single nested group, or a flat list of leaves (legacy → AND).
    if len(filters) == 1 and filters[0].get("op") in _GROUP_OPS:
        root = filters[0]
    else:
        root = {"op": "and", "filters": list(filters)}

    # Scope to a region by default. yfinance's screener is GLOBAL — without a region
    # filter an EquityQuery returns foreign listings and junk (e.g. *.T Tokyo, *.CL).
    # Default to US so this behaves as a US screener; caller can pass region=None to
    # opt out, or include their own region filter (then we don't double-add). Fund
    # queries have no region field, so skip them.
    if region and query_type in ("equity", "etf") and not _has_field(root, "region"):
        root = {"op": "and", "filters": [root, {"op": "eq", "field": "region", "value": region}]}

    query = _build_query(query_class, root)
    if query is None:
        return []

    response = yf.screen(query, sortField=sort_field, sortAsc=sort_asc, size=size, offset=offset)
    quotes = response.get("quotes", [])
    return [_map_screen_quote(q) for q in quotes[:size]]
