"""AI Observability dashboard endpoints — view LLM and tool execution metrics."""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.observe import LLMTrace, ToolTrace
from app.api.v1.endpoints.kestrel.admin import _require_admin
from app.db.session import get_session
from app.schemas.observe import (
    CacheEfficiencyResponse,
    DailyCostResponse,
    ModelUsageResponse,
    ObserveSummary,
    RecentTracesResponse,
    ToolUsageResponse,
)

router = APIRouter(prefix="/observe", tags=["Observability"], dependencies=[Depends(_require_admin)])


@router.get("/summary", response_model=ObserveSummary)
async def get_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """High-level metrics: total cost, tokens, calls, avg latency."""
    since = date.today() - timedelta(days=days)

    stmt = select(
        func.count(LLMTrace.id).label("total_calls"),
        func.sum(LLMTrace.input_tokens).label("total_input_tokens"),
        func.sum(LLMTrace.output_tokens).label("total_output_tokens"),
        func.sum(LLMTrace.cache_read_tokens).label("total_cache_read"),
        func.sum(LLMTrace.cost_usd).label("total_cost"),
        func.avg(LLMTrace.latency_ms).label("avg_latency_ms"),
        func.avg(LLMTrace.time_to_first_token_ms).label("avg_ttft_ms"),
    ).where(LLMTrace.created_at >= since.isoformat())

    result = await db.execute(stmt)
    row = result.one()

    tool_stmt = select(
        func.count(ToolTrace.id).label("total_tool_calls"),
        func.avg(ToolTrace.duration_ms).label("avg_tool_duration_ms"),
        func.sum(func.cast(ToolTrace.success.is_(False), Integer)).label("tool_errors"),
    ).where(ToolTrace.created_at >= since.isoformat())
    tool_result = await db.execute(tool_stmt)
    tool_row = tool_result.one()

    return {
        "period_days": days,
        "llm": {
            "total_calls": row.total_calls or 0,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_cache_read_tokens": row.total_cache_read or 0,
            "total_cost_usd": round(row.total_cost or 0, 4),
            "avg_latency_ms": round(row.avg_latency_ms or 0),
            "avg_ttft_ms": round(row.avg_ttft_ms or 0),
        },
        "tools": {
            "total_calls": tool_row.total_tool_calls or 0,
            "avg_duration_ms": round(tool_row.avg_tool_duration_ms or 0),
            "error_count": tool_row.tool_errors or 0,
        },
    }


@router.get("/by-model", response_model=ModelUsageResponse)
async def get_by_model(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Cost and performance breakdown per model."""
    since = date.today() - timedelta(days=days)

    stmt = select(
        LLMTrace.model,
        func.count(LLMTrace.id).label("calls"),
        func.sum(LLMTrace.input_tokens).label("input_tokens"),
        func.sum(LLMTrace.output_tokens).label("output_tokens"),
        func.sum(LLMTrace.cache_read_tokens).label("cache_read"),
        func.sum(LLMTrace.cost_usd).label("cost"),
        func.avg(LLMTrace.latency_ms).label("avg_latency"),
        func.avg(LLMTrace.time_to_first_token_ms).label("avg_ttft"),
    ).where(
        LLMTrace.created_at >= since.isoformat()
    ).group_by(LLMTrace.model)

    result = await db.execute(stmt)
    rows = result.all()

    return {
        "data": [
            {
                "model": r.model,
                "calls": r.calls,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "cache_read_tokens": r.cache_read or 0,
                "cost_usd": round(r.cost or 0, 4),
                "avg_latency_ms": round(r.avg_latency or 0),
                "avg_ttft_ms": round(r.avg_ttft or 0) if r.avg_ttft else None,
            }
            for r in rows
        ]
    }


@router.get("/by-tool", response_model=ToolUsageResponse)
async def get_by_tool(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Tool execution performance breakdown."""
    since = date.today() - timedelta(days=days)

    stmt = select(
        ToolTrace.tool_name,
        func.count(ToolTrace.id).label("calls"),
        func.avg(ToolTrace.duration_ms).label("avg_duration"),
        func.max(ToolTrace.duration_ms).label("max_duration"),
        func.sum(func.cast(ToolTrace.success.is_(False), Integer)).label("errors"),
    ).where(
        ToolTrace.created_at >= since.isoformat()
    ).group_by(ToolTrace.tool_name).order_by(func.count(ToolTrace.id).desc())

    result = await db.execute(stmt)
    rows = result.all()

    return {
        "data": [
            {
                "tool": r.tool_name,
                "calls": r.calls,
                "avg_duration_ms": round(r.avg_duration or 0),
                "max_duration_ms": r.max_duration or 0,
                "error_count": r.errors or 0,
                "error_rate": round((r.errors or 0) / r.calls * 100, 1) if r.calls else 0,
            }
            for r in rows
        ]
    }


@router.get("/recent", response_model=RecentTracesResponse)
async def get_recent_traces(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Recent LLM calls with full details."""
    stmt = select(LLMTrace).order_by(LLMTrace.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    traces = result.scalars().all()

    return {
        "data": [
            {
                "id": t.id,
                "model": t.model,
                "provider": t.provider,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
                "cache_read_tokens": t.cache_read_tokens,
                "cost_usd": t.cost_usd,
                "latency_ms": t.latency_ms,
                "ttft_ms": t.time_to_first_token_ms,
                "stop_reason": t.stop_reason,
                "is_fallback": t.is_fallback,
                "error": t.error,
                "iteration": t.iteration,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ]
    }


@router.get("/cost-daily", response_model=DailyCostResponse)
async def get_daily_cost(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Daily cost trend for charting."""
    since = date.today() - timedelta(days=days)

    stmt = select(
        func.date(LLMTrace.created_at).label("day"),
        func.sum(LLMTrace.cost_usd).label("cost"),
        func.sum(LLMTrace.input_tokens + LLMTrace.output_tokens).label("tokens"),
        func.count(LLMTrace.id).label("calls"),
    ).where(
        LLMTrace.created_at >= since.isoformat()
    ).group_by(func.date(LLMTrace.created_at)).order_by(func.date(LLMTrace.created_at))

    result = await db.execute(stmt)
    rows = result.all()

    return {
        "data": [
            {
                "date": str(r.day),
                "cost_usd": round(r.cost or 0, 4),
                "tokens": r.tokens or 0,
                "calls": r.calls or 0,
            }
            for r in rows
        ]
    }


@router.get("/cache-efficiency", response_model=CacheEfficiencyResponse)
async def get_cache_efficiency(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Prompt caching hit rate and savings."""
    since = date.today() - timedelta(days=days)

    stmt = select(
        func.sum(LLMTrace.input_tokens).label("total_input"),
        func.sum(LLMTrace.cache_read_tokens).label("cache_hits"),
        func.sum(LLMTrace.cache_creation_tokens).label("cache_creates"),
        func.count(LLMTrace.id).label("total_calls"),
    ).where(
        LLMTrace.created_at >= since.isoformat(),
        LLMTrace.provider == "claude",
    )

    result = await db.execute(stmt)
    row = result.one()

    total_input = row.total_input or 0
    cache_hits = row.cache_hits or 0
    cache_creates = row.cache_creates or 0

    hit_rate = (cache_hits / total_input * 100) if total_input > 0 else 0
    # Savings: cache_read costs 10% of input, so savings = cache_hits * 0.9 * input_price
    estimated_savings = cache_hits * 2.7 / 1_000_000  # 90% of $3/M saved

    return {
        "total_input_tokens": total_input,
        "cache_read_tokens": cache_hits,
        "cache_creation_tokens": cache_creates,
        "cache_hit_rate_pct": round(hit_rate, 1),
        "estimated_savings_usd": round(estimated_savings, 4),
        "total_calls": row.total_calls or 0,
    }


@router.get("/chatanywhere-usage")
async def get_chatanywhere_usage(
    hours: int = Query(24, ge=1, le=720),
    model: str = Query("%", description="Model name pattern, '%' = all (SQL LIKE)"),
) -> dict[str, Any]:
    """Proxy ChatAnywhere's usage_details query (admin) — hourly token/cost usage.

    Lets the AI observability dashboard show free-tier consumption against the daily
    quota. Transport lives in ChatAnywhereUsageClient (providers layer).
    """
    from app.agent.router import CHATANYWHERE_BASE_URL
    from app.dependencies import get_settings
    from app.providers.chatanywhere_usage import ChatAnywhereUsageClient

    client = ChatAnywhereUsageClient(
        api_key=getattr(get_settings(), "chat_anywhere_api_key", None),
        base_url=CHATANYWHERE_BASE_URL,
    )
    result = await client.get_usage(hours=hours, model=model)
    return result.to_dict()
