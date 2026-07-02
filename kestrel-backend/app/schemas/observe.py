from typing import Any

from pydantic import BaseModel, Field


class ObserveSummary(BaseModel):
    period_days: int = 7
    llm: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)


class ModelUsageItem(BaseModel):
    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    avg_ttft_ms: float | None = None


class ModelUsageResponse(BaseModel):
    data: list[ModelUsageItem] = Field(default_factory=list)


class ToolUsageItem(BaseModel):
    tool: str
    calls: int = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0


class ToolUsageResponse(BaseModel):
    data: list[ToolUsageItem] = Field(default_factory=list)


class RecentTraceItem(BaseModel):
    id: str
    model: str | None = None
    provider: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    ttft_ms: int | None = None
    stop_reason: str | None = None
    is_fallback: bool = False
    error: str | None = None
    iteration: int = 1
    created_at: str | None = None


class RecentTracesResponse(BaseModel):
    data: list[RecentTraceItem] = Field(default_factory=list)


class DailyCostItem(BaseModel):
    date: str
    cost_usd: float = 0.0
    tokens: int = 0
    calls: int = 0


class DailyCostResponse(BaseModel):
    data: list[DailyCostItem] = Field(default_factory=list)


class CacheEfficiencyResponse(BaseModel):
    total_input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_hit_rate_pct: float = 0.0
    estimated_savings_usd: float = 0.0
    total_calls: int = 0
