"""ETF data endpoints — real-time NAV, premium/discount, holdings, popular list."""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_cache, get_etf_service, get_market_cache
from app.providers.cache import CacheBackend, build_cache_key
from app.schemas.common import DataListResponse, DataResponse
from app.services.data.etf_service import ETFService

if TYPE_CHECKING:
    from app.db.duckdb.market_cache import MarketDataCache

router = APIRouter(prefix="/etf", tags=["ETF"])


@router.get("/nav", response_model=DataListResponse)
async def get_etf_nav() -> dict[str, Any]:
    """Get all ETF real-time NAV and premium/discount data.

    Returns: etf_id, name, market_price, estimated_nav, premium_discount_pct,
    prev_nav, issued_units, unit_change, data_date, data_time, market_type.
    Source: mis.twse.com.tw/stock/data/all_etf.txt (real-time, ~343 ETFs).
    """
    from app.scrapers.twse_etf import scrape_etf_nav
    try:
        data = await scrape_etf_nav()
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/nav/{etf_id}", response_model=DataResponse)
async def get_etf_nav_single(etf_id: str) -> dict[str, Any]:
    """Get single ETF real-time NAV and premium/discount."""
    from app.scrapers.twse_etf import scrape_etf_nav
    try:
        data = await scrape_etf_nav()
        match = [d for d in data if d["etf_id"] == etf_id]
        if match:
            return {"data": match[0]}
        return {"data": None, "error": f"ETF {etf_id} not found"}
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}


@router.get("/{etf_id}/profile", response_model=DataResponse)
async def get_etf_profile(
    etf_id: str,
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """ETF fund profile + derived figures for the detail page 總覽.

    Merges TWSE OpenAPI fund-info (manager / custodian / inception / listing / issued
    units / fund type — cached 24h since it changes rarely) with the live NAV scrape to
    derive 資產規模 (AUM = issued_units × NAV), 成立年數, and 年化報酬(成立以來)
    (annualized from listing-reference 上市 to current NAV). Returns null when the ETF
    isn't in the fund table.
    """
    from datetime import date as _date

    from app.scrapers.twse_etf import scrape_etf_fund_info, scrape_etf_nav

    # Fund-info map — cached 24h (rarely changes).
    info_key = build_cache_key("etf", "fund_info_all")
    info_map = await cache.get(info_key)
    if not info_map:
        info_map = await scrape_etf_fund_info()
        if info_map:
            await cache.set(info_key, info_map, ttl=86400)
    profile = (info_map or {}).get(etf_id)
    if not profile:
        return {"data": None, "error": f"ETF {etf_id} not in fund table"}

    # Live NAV for AUM + premium.
    nav_row: dict[str, Any] = {}
    try:
        nav_all = await scrape_etf_nav()
        nav_row = next((d for d in nav_all if d.get("etf_id") == etf_id), {})
    except Exception:
        pass

    def _f(v: Any) -> float | None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    units = _f(profile.get("issued_units"))
    nav = _f(nav_row.get("estimated_nav"))
    market_price = _f(nav_row.get("market_price"))
    aum = units * nav if units and nav else None

    # Expense ratio (總費用率) — not in any official feed; sourced from CMoney and
    # cached per-ETF 24h. Best-effort: a miss just omits the expense fields.
    cm_key = build_cache_key("etf", "cmoney", etf_id=etf_id)
    cmoney = await cache.get(cm_key)
    if cmoney is None:
        from app.scrapers.cmoney_etf import scrape_cmoney_etf
        cmoney = await scrape_cmoney_etf(etf_id)
        if cmoney:
            await cache.set(cm_key, cmoney, ttl=86400)
    cmoney = cmoney or {}

    # 成立年數 from the listing date.
    inception_years: float | None = None
    listing = profile.get("listing_date")
    ld: _date | None = None
    if listing:
        try:
            ld = _date.fromisoformat(listing)
            inception_years = round((_date.today() - ld).days / 365.25, 1)
        except ValueError:
            ld = None

    # 持股人數 (受益人數) — TDCC dispersion table, cached 24h (weekly feed).
    holder_count = None
    hc_key = build_cache_key("etf", "holder_counts")
    hc_map = await cache.get(hc_key)
    if hc_map is None:
        from app.scrapers.tdcc_holders import scrape_holder_counts
        hc_map = await scrape_holder_counts()
        if hc_map:
            await cache.set(hc_key, hc_map, ttl=86400)
    if hc_map:
        holder_count = hc_map.get(etf_id)

    # 年化報酬(成立以來) — annualized total price return from listing to latest close,
    # computed from FinMind ETF price history (cached per-ETF 24h). Needs ≥ ~30 days
    # listed to be meaningful.
    from app.services.data.etf_metrics import annualized_return_since_listing
    annualized = await annualized_return_since_listing(cache, etf_id, ld)

    return {
        "data": {
            **profile,
            "market_price": market_price,
            "nav": nav,
            "premium_discount_pct": _f(nav_row.get("premium_discount_pct")),
            "aum": aum,
            "inception_years": inception_years,
            "expense_ratio_pct": cmoney.get("expense_ratio_pct"),
            "management_fee_pct": cmoney.get("management_fee_pct"),
            "custody_fee_pct": cmoney.get("custody_fee_pct"),
            "holder_count": holder_count,
            "annualized_return_pct": annualized,
            "yield_pct": cmoney.get("yield_pct"),
            "beta": cmoney.get("beta"),
            "std_dev": cmoney.get("std_dev"),
            "alpha": cmoney.get("alpha"),
            "tracking_error_pct": cmoney.get("tracking_error_pct"),
        }
    }


@router.get("/{etf_id}/premium-history", response_model=DataListResponse)
async def get_etf_premium_history(
    etf_id: str,
    days: int = Query(default=90, ge=1, le=365),
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> dict[str, Any]:
    """Daily 折溢價 (premium/discount) + NAV vs market-price history for one ETF.

    Series is persisted nightly by the daily ingest (TWSE MIS NAV snapshot →
    etf_nav_daily); the live NAV feed alone is point-in-time. Empty until the ingest
    has run for at least one session.
    """
    if market_cache is None:
        return {"data": [], "count": 0}
    start = date.today() - timedelta(days=days)
    try:
        rows = await market_cache.get_etf_nav_history(etf_id, start)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}
    return {"data": rows, "count": len(rows)}


@router.get("/{etf_id}/holdings", response_model=DataListResponse)
async def get_etf_holdings(
    etf_id: str,
    target_date: date | None = Query(None),
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """Top holdings (成分股) for an ETF, with weights.

    Sourced from CMoney (cached per-ETF 24h) — the legacy TWSE holdings endpoint is
    dead (404). Returns up to 10 holdings as {name, weight}. Falls back to the TWSE
    scraper if CMoney yields nothing (kept as a cross-check path)."""
    cm_key = build_cache_key("etf", "cmoney", etf_id=etf_id)
    cmoney = await cache.get(cm_key)
    if cmoney is None:
        from app.scrapers.cmoney_etf import scrape_cmoney_etf
        cmoney = await scrape_cmoney_etf(etf_id)
        if cmoney:
            await cache.set(cm_key, cmoney, ttl=86400)
    holdings = (cmoney or {}).get("top_holdings") or []
    if holdings:
        return {"data": holdings, "count": len(holdings)}

    # Cross-check fallback: the (usually-dead) TWSE composition endpoint.
    from app.scrapers.twse_etf import scrape_etf_holdings
    try:
        data = await scrape_etf_holdings(etf_id, target_date)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/{etf_id}/dividends", response_model=DataListResponse)
async def get_etf_dividends(
    etf_id: str,
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """配息紀錄 — an ETF's recent cash-dividend history: {ex_date, cash_dividend,
    yield_pct} newest first. Sourced from CMoney (shared 24h cache with the profile/
    holdings endpoints). Empty for non-distributing ETFs."""
    cm_key = build_cache_key("etf", "cmoney", etf_id=etf_id)
    cmoney = await cache.get(cm_key)
    if cmoney is None:
        from app.scrapers.cmoney_etf import scrape_cmoney_etf
        cmoney = await scrape_cmoney_etf(etf_id)
        if cmoney:
            await cache.set(cm_key, cmoney, ttl=86400)
    dividends = (cmoney or {}).get("dividends") or []
    return {"data": dividends, "count": len(dividends)}


@router.get("/{etf_id}/operations", response_model=DataResponse)
async def get_etf_operations(
    etf_id: str,
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> dict[str, Any]:
    """操作日報 — an active ETF's holdings changes (加碼/減碼/新增/刪除) between its two
    most recent daily snapshots. Snapshots are persisted nightly (etf_holdings_daily);
    the log is empty until ≥2 sessions have been collected."""
    if market_cache is None:
        return {"data": {"latest": None, "prior": None, "ops": []}}
    try:
        return {"data": await market_cache.get_etf_holdings_ops(etf_id)}
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}


@router.get("/{etf_id}/sectors", response_model=DataResponse)
async def get_etf_sectors(
    etf_id: str,
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """產業分佈 — the ETF's holdings weight aggregated by industry.

    Maps each MoneyDJ holding → stock industry (FinMind industry_category) and sums
    weight%. Foreign/bond holdings (no TW industry) roll into other_pct. Cached 24h."""
    from app.services.data.active_etf_service import get_sector_breakdown
    try:
        return {"data": await get_sector_breakdown(cache, etf_id)}
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}


@router.get("/active-holders/{stock_id}", response_model=DataResponse)
async def get_active_etf_holders(
    stock_id: str,
    cache: CacheBackend = Depends(get_cache),
) -> dict[str, Any]:
    """持有主動式ETF — which 主動式ETF (active ETFs) hold this stock, and how much.

    Inverts the full holdings of the active-ETF universe (~30 ETFs, sourced from
    MoneyDJ which lists the COMPLETE constituent list, not just top-10). Per holder:
    etf_id, etf_name, weight_pct, shares_lots (張), est_value (≈ AUM × weight%, derived).
    Plus aggregate count + total est value. Index built once and cached 24h."""
    from app.services.data.active_etf_service import get_active_holders
    try:
        result = await get_active_holders(cache, stock_id)
        return {"data": result}
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}


@router.get("/premium-discount", response_model=DataListResponse)
async def get_etf_premium_discount(threshold: float = Query(default=1.0)) -> dict[str, Any]:
    """Get ETFs with significant premium or discount (abs > threshold %).

    Useful for finding mispriced ETFs for arbitrage or entry signals.
    """
    from app.scrapers.twse_etf import scrape_etf_nav
    try:
        data = await scrape_etf_nav()
        significant = [
            d for d in data
            if isinstance(d.get("premium_discount_pct"), (int, float))
            and abs(d["premium_discount_pct"]) >= threshold
        ]
        significant.sort(key=lambda x: abs(x["premium_discount_pct"]), reverse=True)
        return {"data": significant, "count": len(significant), "threshold": threshold}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/list", response_model=DataListResponse)
async def get_etf_list(
    start_date: date | None = Query(None),
    service: ETFService = Depends(get_etf_service),
) -> dict[str, Any]:
    """Get list of popular ETFs with price data (cache-first, sorted by volume).

    Delegates to ETFService: the two FinMind fetches run only on a cache miss and
    use the shared provider registry, so the request path no longer blocks on
    per-request provider init + two live API calls.
    """
    trade_date = start_date or date.today()
    try:
        return await service.get_popular_etfs(trade_date)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}
