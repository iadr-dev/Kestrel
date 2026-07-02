"""Active-ETF (主動式ETF) holdings inversion.

Answers the 持有主動式ETF panel: "which active ETFs hold stock X, and how much".

How it works:
1. The active-ETF universe is the ~30 ETFs whose code ends in 'A' (or whose name
   starts 主動), taken from the TWSE OpenAPI fund-info feed we already scrape.
2. For each active ETF we pull its FULL holdings from MoneyDJ (CMoney only SSRs the
   top-10, which misses small positions — see moneydj_etf.py) → {name, 張數, weight%}.
3. We invert that into stock_name → [ (etf_id, weight%, 張數) ], and resolve each ETF's
   AUM (issued_units × NAV) so we can derive 持股市值 ≈ AUM × weight%.
4. Lookup by stock_id: resolve the stock's name(s) via TaiwanStockInfo and match.

The whole inverted index is expensive to build (~30 page scrapes) but identical for
every caller and slow-moving, so it's cached 24h as one blob and every per-stock
request reads from it.
"""

import asyncio
from typing import Any, cast

from app.core.logging import get_logger
from app.providers.cache import CacheBackend, build_cache_key

log = get_logger(__name__)

# Concurrency for the ~30 MoneyDJ scrapes — gentle on the source, fast enough.
_SCRAPE_CONCURRENCY = 6
_INDEX_TTL = 86400  # 24h


def _norm_name(s: str | None) -> str:
    """Normalize a holding/company name for matching: drop the odd-lot/full-share
    markers and whitespace MoneyDJ vs TaiwanStockInfo differ on (e.g. '國巨*' → '國巨')."""
    return (s or "").replace("*", "").replace(" ", "").replace("　", "").strip()


async def _active_etf_ids(cache: CacheBackend) -> dict[str, str]:
    """{etf_id: short_name} for the active-ETF universe (code endswith 'A' or 主動 name).
    Reuses the cached fund-info blob the profile endpoint populates."""
    info_key = build_cache_key("etf", "fund_info_all")
    info_map = await cache.get(info_key)
    if not info_map:
        from app.scrapers.twse_etf import scrape_etf_fund_info
        info_map = await scrape_etf_fund_info()
        if info_map:
            await cache.set(info_key, info_map, ttl=_INDEX_TTL)
    out: dict[str, str] = {}
    for code, prof in (info_map or {}).items():
        name = prof.get("short_name") or prof.get("name") or ""
        if code.endswith("A") or name.startswith("主動"):
            out[code] = name
    return out


async def _etf_aum(cache: CacheBackend, etf_id: str, units_str: str | None) -> float | None:
    """資產規模 ≈ issued_units × NAV. Units come from fund-info; NAV from the live MIS
    scrape (cached all-ETF blob)."""
    units = None
    try:
        units = float(str(units_str).replace(",", "")) if units_str else None
    except (TypeError, ValueError):
        units = None
    if not units:
        return None
    nav_key = build_cache_key("etf", "nav_all")
    nav_all = await cache.get(nav_key)
    if not nav_all:
        from app.scrapers.twse_etf import scrape_etf_nav
        nav_all = await scrape_etf_nav()
        if nav_all:
            await cache.set(nav_key, nav_all, ttl=3600)
    nav_row = next((d for d in (nav_all or []) if d.get("etf_id") == etf_id), None)
    if not nav_row:
        return None
    try:
        nav = float(str(nav_row.get("estimated_nav")).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return units * nav if nav else None


async def _build_index(cache: CacheBackend) -> dict[str, Any]:
    """Build the inverted index: normalized-holding-name → list of holder ETFs.

    Returns {"by_name": {norm_name: [{etf_id, etf_name, weight_pct, shares_lots,
    est_value}]}, "etf_count": n}. est_value = AUM × weight% (approximate — derived,
    not an exact 持股市值 feed)."""
    from app.scrapers.twse_etf import scrape_etf_fund_info

    info_map = await cache.get(build_cache_key("etf", "fund_info_all")) or await scrape_etf_fund_info()
    active = await _active_etf_ids(cache)

    sem = asyncio.Semaphore(_SCRAPE_CONCURRENCY)

    async def fetch(etf_id: str) -> tuple[str, list[dict[str, Any]], float | None]:
        from app.scrapers.moneydj_etf import scrape_moneydj_holdings
        async with sem:
            holdings = await scrape_moneydj_holdings(etf_id)
        aum = await _etf_aum(cache, etf_id, (info_map or {}).get(etf_id, {}).get("issued_units"))
        return etf_id, holdings, aum

    results = await asyncio.gather(*[fetch(e) for e in active], return_exceptions=True)

    by_name: dict[str, list[dict[str, Any]]] = {}
    for res in results:
        if isinstance(res, BaseException):
            continue
        etf_id, holdings, aum = res
        etf_name = active.get(etf_id, etf_id)
        for h in holdings:
            nm = _norm_name(h.get("name"))
            if not nm:
                continue
            weight = h.get("weight_pct")
            est_value = (aum * weight / 100.0) if (aum and weight) else None
            by_name.setdefault(nm, []).append({
                "etf_id": etf_id,
                "etf_name": etf_name,
                "weight_pct": weight,
                "shares_lots": h.get("shares_lots"),
                "est_value": est_value,
            })
    return {"by_name": by_name, "etf_count": len(active)}


async def get_inverted_index(cache: CacheBackend) -> dict[str, Any]:
    """Cached active-ETF inverted index (build on miss)."""
    key = build_cache_key("etf", "active_holders_index")
    cached = await cache.get(key)
    if cached:
        return cast(dict[str, Any], cached)
    index = await _build_index(cache)
    if index.get("by_name"):
        await cache.set(key, index, ttl=_INDEX_TTL)
    return index


async def get_sector_breakdown(cache: CacheBackend, etf_id: str) -> dict[str, Any]:
    """ETF 產業分佈: aggregate the ETF's full holdings (MoneyDJ) weight by industry,
    resolving each holding name → industry via TaiwanStockInfo's industry_category.

    Returns {"sectors": [{industry, weight_pct}], "matched_pct", "other_pct"} sorted
    desc. Cached per-ETF 24h. Foreign/bond holdings (no TW industry) fall into 其他."""
    key = build_cache_key("etf", "sectors", etf_id=etf_id)
    cached = await cache.get(key)
    if cached is not None:
        return cast(dict[str, Any], cached)

    from app.scrapers.moneydj_etf import scrape_moneydj_holdings
    holdings = await scrape_moneydj_holdings(etf_id)
    if not holdings:
        return {"sectors": [], "matched_pct": 0.0, "other_pct": 0.0}

    name2ind = await _name_to_industry()
    sectors: dict[str, float] = {}
    matched = 0.0
    other = 0.0
    for h in holdings:
        weight = h.get("weight_pct") or 0.0
        ind = name2ind.get(_norm_name(h.get("name")))
        if ind:
            sectors[ind] = sectors.get(ind, 0.0) + weight
            matched += weight
        else:
            other += weight

    ranked = sorted(
        ({"industry": k, "weight_pct": round(v, 2)} for k, v in sectors.items()),
        key=lambda s: cast(float, s["weight_pct"]),
        reverse=True,
    )
    result = {
        "sectors": ranked,
        "matched_pct": round(matched, 2),
        "other_pct": round(other, 2),
    }
    if ranked:
        await cache.set(key, result, ttl=_INDEX_TTL)
    return result


async def _name_to_industry() -> dict[str, str]:
    """{normalized_stock_name: industry_category} from TaiwanStockInfo."""
    out: dict[str, str] = {}
    try:
        from app.core.config import Settings
        from app.core.constants import FinMindDataset
        from app.providers.finmind.provider import FinMindProvider
        provider = FinMindProvider(Settings())
        await provider.initialize()
        try:
            info = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        finally:
            await provider.close()
        for row in info or []:
            nm = _norm_name(row.get("stock_name"))
            ind = row.get("industry_category")
            if nm and ind:
                out.setdefault(nm, ind)
    except Exception as e:
        log.warning("active_etf_industry_map_failed", error=str(e)[:100])
    return out


async def _stock_names(stock_id: str) -> set[str]:
    """Normalized name(s) for a stock_id, from TaiwanStockInfo. A holding may be listed
    under the short name (上銀) or, rarely, a longer variant; we match on the short name
    plus any name the info feed carries."""
    names: set[str] = set()
    try:
        from app.core.config import Settings
        from app.core.constants import FinMindDataset
        from app.providers.finmind.provider import FinMindProvider
        provider = FinMindProvider(Settings())
        await provider.initialize()
        try:
            info = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        finally:
            await provider.close()
        for row in info or []:
            if row.get("stock_id") == stock_id and row.get("stock_name"):
                names.add(_norm_name(row["stock_name"]))
    except Exception as e:
        log.warning("active_etf_stock_name_lookup_failed", stock_id=stock_id, error=str(e)[:100])
    return names


async def get_active_holders(cache: CacheBackend, stock_id: str) -> dict[str, Any]:
    """Active ETFs holding `stock_id`, with aggregate stats for the 持有主動式ETF panel."""
    index = await get_inverted_index(cache)
    by_name: dict[str, list[dict[str, Any]]] = index.get("by_name", {})

    names = await _stock_names(stock_id)
    holders: list[dict[str, Any]] = []
    seen: set[str] = set()
    for nm in names:
        for h in by_name.get(nm, []):
            if h["etf_id"] in seen:
                continue
            seen.add(h["etf_id"])
            holders.append(h)

    holders.sort(key=lambda h: (h.get("est_value") or 0, h.get("weight_pct") or 0), reverse=True)
    total_value = sum(h["est_value"] for h in holders if h.get("est_value"))
    return {
        "stock_id": stock_id,
        "holders": holders,
        "count": len(holders),
        "total_est_value": total_value or None,
        "active_etf_universe": index.get("etf_count", 0),
    }
