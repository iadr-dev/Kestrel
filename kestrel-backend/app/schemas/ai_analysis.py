from typing import Any

from pydantic import BaseModel, Field


class StockRankingItem(BaseModel):
    stock_id: str
    stock_name: str | None = None
    technical_score: float | None = None
    chip_score: float | None = None
    fundamental_score: float | None = None
    theme_score: float | None = None
    overall_score: float | None = None


class RankingsResponse(BaseModel):
    data: list[StockRankingItem] = Field(default_factory=list)
    count: int = 0
    sort: str | None = None
    # Tier gating: free users get the top FREE_PREVIEW_ROWS; `total` is the full count
    # and `locked` signals the frontend to render the "show top N, blur rest" strip.
    locked: bool = False
    total: int | None = None
    required_tier: str | None = None


class StockSummary(BaseModel):
    stock_id: str
    position_label: str | None = None
    summary: str | None = None
    factors: list[str] = Field(default_factory=list)
    swot: dict[str, Any] | None = None
    generated_at: str | None = None


class StockSummaryResponse(BaseModel):
    data: StockSummary | None = None
    message: str | None = None
    # Tier gating: when the caller's tier can't access this AI feature, `data` is
    # withheld, `locked` is true and `required_tier` names the tier that unlocks it.
    locked: bool = False
    required_tier: str | None = None


class ScoreBreakdown(BaseModel):
    stock_id: str
    technical: float | None = None
    chip: float | None = None
    fundamental: float | None = None
    theme: float | None = None
    overall: float | None = None
    details: dict[str, Any] | None = None


class ScoreResponse(BaseModel):
    data: ScoreBreakdown | None = None
    message: str | None = None
    # Tier gating (see StockSummaryResponse).
    locked: bool = False
    required_tier: str | None = None
