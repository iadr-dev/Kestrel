from typing import Any

from pydantic import BaseModel, Field


class ThemeItem(BaseModel):
    # Mirrors ThemeRepository.list_themes() exactly. Fields the repo does not
    # produce were previously declared here (name/description/category) and made
    # FastAPI emit phantom nulls, while fields it DOES produce (name_en,
    # sub_industries) were silently stripped — breaking the frontend.
    id: str
    name_zh: str | None = None
    name_en: str | None = None
    stock_count: int | None = None
    sub_industries: list[str] = Field(default_factory=list)


class ThemeListResponse(BaseModel):
    data: list[ThemeItem] = Field(default_factory=list)
    count: int = 0


class ThemeStockItem(BaseModel):
    stock_id: str
    stock_name: str | None = None
    tier: str | None = None
    relevance: float | None = None


class ThemeStocksResponse(BaseModel):
    data: list[ThemeStockItem] = Field(default_factory=list)
    count: int = 0
    theme_id: str | None = None


class ThemeTiersResponse(BaseModel):
    data: dict[str, list[Any]] = Field(default_factory=dict)
    theme_id: str | None = None
    tier_defined: bool = False


class SupplyChainEdge(BaseModel):
    source: str | None = None
    target: str | None = None
    relationship: str | None = None
    weight: float | None = None


class SupplyChainResponse(BaseModel):
    data: list[SupplyChainEdge] = Field(default_factory=list)
    count: int = 0
    stock_id: str | None = None


class SupplyChainGraphResponse(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    theme_id: str | None = None


class ThemeStructureResponse(BaseModel):
    """Enriched member list for the industry-structure modal (role grouping + comparison)."""
    theme_id: str | None = None
    members: list[dict[str, Any]] = Field(default_factory=list)
    tier_defined: bool = False
