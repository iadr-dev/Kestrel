"""Theme/industry endpoints — served from DuckDB (ThemeRepository).

Source of truth is DuckDB (seeded from FinMind industry chain; supply-chain edges
from LLM extraction). Replaces the former data/*.json files. Response shapes are
unchanged so the frontend needs no updates.
"""

from typing import Any

from fastapi import APIRouter, Query

from app.schemas.common import DataListResponse, DataResponse
from app.schemas.themes import (
    SupplyChainGraphResponse,
    SupplyChainResponse,
    ThemeListResponse,
    ThemeStocksResponse,
    ThemeStructureResponse,
    ThemeTiersResponse,
)
from app.services.data.theme_repository import ThemeRepository

router = APIRouter(prefix="/themes", tags=["Themes"])


def _repo() -> ThemeRepository:
    return ThemeRepository()


@router.get("", response_model=ThemeListResponse)
async def get_themes() -> dict[str, Any]:
    """Get all active themes with stock counts and sub-industries."""
    themes = await _repo().list_themes()
    return {"data": themes, "count": len(themes)}


@router.get("/{theme_id}/stocks", response_model=ThemeStocksResponse)
async def get_theme_stocks(
    theme_id: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get stocks belonging to a specific theme."""
    stocks = await _repo().get_theme_stocks(theme_id, limit=limit)
    return {"data": stocks, "count": len(stocks), "theme_id": theme_id}


@router.get("/search", response_model=DataListResponse)
async def search_themes(
    q: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Search themes by name."""
    results = await _repo().search_themes(q)
    return {"data": results, "count": len(results)}


@router.get("/{theme_id}/tiers", response_model=ThemeTiersResponse)
async def get_theme_tiers(theme_id: str) -> dict[str, Any]:
    """Get stocks grouped by upstream/midstream/downstream tiers for a theme."""
    return await _repo().get_theme_tiers(theme_id)


@router.get("/{theme_id}/structure", response_model=ThemeStructureResponse)
async def get_theme_structure(
    theme_id: str,
    limit: int = Query(200, ge=1, le=500),
) -> dict[str, Any]:
    """Enriched members (tier + relevance + edge degree + latest price) for the
    industry-structure modal — powers role-grouping and comparison in one call."""
    return await _repo().get_theme_structure(theme_id, limit=limit)


# === Supply Chain Endpoints ===


@router.get("/supply-chain/stock/{stock_id}", response_model=SupplyChainResponse)
async def get_stock_relationships(stock_id: str) -> dict[str, Any]:
    """Get supply chain relationships for a stock."""
    edges = await _repo().get_stock_edges(stock_id)
    return {"data": edges, "count": len(edges), "stock_id": stock_id}


@router.get("/company/{stock_id}/profile", response_model=DataResponse)
async def get_company_profile(stock_id: str) -> dict[str, Any]:
    """Get company profile. TW stocks: TWSE/TPEx OpenAPI (chairman/CEO/spokesman/
    address/capital/dates/website) + FinMind industry. US stocks: yfinance.

    The old MOPS HTML scraper (mops/web/t05st03) is dead — TWSE migrated the site,
    so it returned nothing and the UI showed just the id. We now read the live
    TWSE listed (t187ap03_L) / TPEx OTC (mopsfin_t187ap03_O) OpenAPI feeds, and
    add the FinMind industry_category on top (the OpenAPI feed only carries an
    industry *code*)."""
    # US/Global stocks: yfinance (structured API, no scraping)
    if not (stock_id.isdigit() and len(stock_id) <= 5):
        from app.providers.yfinance import YFinanceProvider
        return {"data": await YFinanceProvider().get_info(stock_id)}

    # TW: live TWSE/TPEx OpenAPI profile (full company info, refreshed daily).
    from app.providers.twse import get_twse_client
    data: dict[str, Any] = {"stock_id": stock_id, "market": "TW"}
    try:
        profile = await get_twse_client().get_company_profile(stock_id)
        if profile:
            data.update(profile)
    except Exception:
        pass

    # FinMind industry_category — readable industry name (OpenAPI only has a code),
    # and a name_zh fallback in case the OpenAPI feed misses this code.
    try:
        from app.core.config import Settings
        from app.core.constants import FinMindDataset
        from app.providers.finmind.provider import FinMindProvider
        provider = FinMindProvider(Settings())
        await provider.initialize()
        try:
            info = await provider.fetch(FinMindDataset.TAIWAN_STOCK_INFO)
        finally:
            await provider.close()
        for row in info or []:
            if row.get("stock_id") == stock_id:
                if row.get("industry_category"):
                    data["industry"] = row["industry_category"]
                if not data.get("name_zh") and row.get("stock_name"):
                    data["name_zh"] = row["stock_name"]
                break
    except Exception:
        pass

    return {"data": data}


@router.get("/supply-chain/graph/{theme_id}", response_model=SupplyChainGraphResponse)
async def get_theme_graph(theme_id: str) -> dict[str, Any]:
    """Get full graph data (nodes + edges) for a theme. For reagraph visualization."""
    return await _repo().get_theme_graph(theme_id)
