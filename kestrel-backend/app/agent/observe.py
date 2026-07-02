"""Kestrel AI Observability — built-in tracing for LLM calls, tool executions, and cost analysis.

Tracks:
- Every LLM call: model, provider, input/output tokens, latency, cache hits, cost
- Every tool execution: name, args summary, duration, success/failure
- Per-turn aggregation: total cost, iterations, stop reason
- Per-session aggregation: conversation depth, cumulative cost
- Historical metrics: daily/model/provider breakdowns for optimization
"""

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid

# ──────────────────────────────────────────────
# DB Models
# ──────────────────────────────────────────────

class LLMTrace(Base):
    """One row per LLM API call."""
    __tablename__ = "llm_traces"
    __table_args__ = (
        Index("ix_llm_traces_user_ts", "user_id", "created_at"),
        Index("ix_llm_traces_model", "model"),
        Index("ix_llm_traces_session", "session_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(String(36))
    turn_id: Mapped[str | None] = mapped_column(String(36))

    model: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(20))

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    time_to_first_token_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stop_reason: Mapped[str | None] = mapped_column(String(30))
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    system_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    iteration: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ToolTrace(Base):
    """One row per tool execution."""
    __tablename__ = "tool_traces"
    __table_args__ = (
        Index("ix_tool_traces_user_ts", "user_id", "created_at"),
        Index("ix_tool_traces_name", "tool_name"),
        Index("ix_tool_traces_turn", "turn_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(String(36))
    turn_id: Mapped[str | None] = mapped_column(String(36))
    llm_trace_id: Mapped[str | None] = mapped_column(String(36))

    tool_name: Mapped[str] = mapped_column(String(100))
    args_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ──────────────────────────────────────────────
# In-memory Span Context (for building traces during streaming)
# ──────────────────────────────────────────────

MODEL_PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_create": 3.75},
    "claude-opus-4-8": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_create": 6.25},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_create": 6.25},
    "claude-haiku-4-5": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_create": 1.0},
    "gpt-5.5": {"input": 5.0, "output": 20.0, "cache_read": 0.5, "cache_create": 0.0},
    "gpt-5.4": {"input": 3.0, "output": 12.0, "cache_read": 0.3, "cache_create": 0.0},
    "gpt-5.4-mini": {"input": 0.6, "output": 2.4, "cache_read": 0.06, "cache_create": 0.0},
    "gpt-5.4-nano": {"input": 0.15, "output": 0.6, "cache_read": 0.015, "cache_create": 0.0},
    "gpt-4o": {"input": 2.5, "output": 10.0, "cache_read": 1.25, "cache_create": 0.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6, "cache_read": 0.075, "cache_create": 0.0},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.6, "cache_read": 0.0, "cache_create": 0.0},
    "gemini-3.5-flash": {"input": 0.15, "output": 0.6, "cache_read": 0.0, "cache_create": 0.0},
    "deepseek-ai/deepseek-v4-flash": {"input": 0.14, "output": 0.28, "cache_read": 0.0028, "cache_create": 0.0},
    "deepseek-ai/deepseek-v4-pro": {"input": 0.435, "output": 0.87, "cache_read": 0.003625, "cache_create": 0.0},
    "minimaxai/minimax-m2.7": {"input": 0.15, "output": 0.6, "cache_read": 0.0, "cache_create": 0.0},
    "meta/llama-4-maverick-17b-128e-instruct": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
    "openrouter/free": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
    "openrouter/auto": {"input": 3.0, "output": 15.0, "cache_read": 0.0, "cache_create": 0.0},
    "chatanywhere/gpt-4o-mini": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
    "chatanywhere/gpt-4o": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
    "chatanywhere/gpt-5-mini": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
    "chatanywhere/deepseek-v3": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_create": 0.0},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int,
                   cache_read: int = 0, cache_create: int = 0) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("openrouter/auto", {}))
    cost = (
        input_tokens * pricing.get("input", 3.0)
        + output_tokens * pricing.get("output", 15.0)
        + cache_read * pricing.get("cache_read", 0.0)
        + cache_create * pricing.get("cache_create", 0.0)
    ) / 1_000_000
    return round(cost, 6)


@dataclass
class LLMSpan:
    """In-flight span for one LLM call."""
    model: str
    provider: str
    start_time: float = field(default_factory=time.perf_counter)
    first_token_time: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    stop_reason: str | None = None
    is_fallback: bool = False
    error: str | None = None
    iteration: int = 1

    def record_first_token(self) -> None:
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()

    def finish(self) -> dict[str, Any]:
        elapsed = time.perf_counter() - self.start_time
        ttft = int((self.first_token_time - self.start_time) * 1000) if self.first_token_time else None
        total = self.input_tokens + self.output_tokens
        cost = calculate_cost(self.model, self.input_tokens, self.output_tokens,
                              self.cache_read_tokens, self.cache_creation_tokens)
        return {
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "total_tokens": total,
            "cost_usd": cost,
            "latency_ms": int(elapsed * 1000),
            "time_to_first_token_ms": ttft,
            "stop_reason": self.stop_reason,
            "is_fallback": self.is_fallback,
            "error": self.error,
            "iteration": self.iteration,
        }


@dataclass
class ToolSpan:
    """In-flight span for one tool execution."""
    tool_name: str
    args_summary: str | None = None
    start_time: float = field(default_factory=time.perf_counter)
    success: bool = True
    error: str | None = None
    result_summary: str | None = None

    def finish(self) -> dict[str, Any]:
        elapsed = time.perf_counter() - self.start_time
        return {
            "tool_name": self.tool_name,
            "args_summary": self.args_summary,
            "result_summary": self.result_summary,
            "duration_ms": int(elapsed * 1000),
            "success": self.success,
            "error": self.error,
        }


@dataclass
class TurnTrace:
    """Aggregates all spans for one agent turn (user message → full response)."""
    user_id: str
    session_id: str | None = None
    turn_id: str | None = None
    llm_spans: list[LLMSpan] = field(default_factory=list)
    tool_spans: list[ToolSpan] = field(default_factory=list)
    start_time: float = field(default_factory=time.perf_counter)

    def start_llm_span(self, model: str, provider: str, iteration: int = 1, is_fallback: bool = False) -> LLMSpan:
        span = LLMSpan(model=model, provider=provider, iteration=iteration, is_fallback=is_fallback)
        self.llm_spans.append(span)
        return span

    def start_tool_span(self, tool_name: str, args_summary: str | None = None) -> ToolSpan:
        span = ToolSpan(tool_name=tool_name, args_summary=args_summary)
        self.tool_spans.append(span)
        return span

    def summary(self) -> dict[str, Any]:
        total_llm_cost = sum(s.finish()["cost_usd"] for s in self.llm_spans)
        total_tokens = sum(s.finish()["total_tokens"] for s in self.llm_spans)
        total_latency = int((time.perf_counter() - self.start_time) * 1000)
        return {
            "turn_id": self.turn_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "total_cost_usd": round(total_llm_cost, 6),
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency,
            "llm_calls": len(self.llm_spans),
            "tool_calls": len(self.tool_spans),
            "iterations": max((s.iteration for s in self.llm_spans), default=1),
            "models_used": list({s.model for s in self.llm_spans}),
        }


# ──────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────

async def persist_turn_trace(trace: TurnTrace, db: Any) -> None:
    """Write all spans from a completed turn to the database."""
    for span in trace.llm_spans:
        data = span.finish()
        record = LLMTrace(
            user_id=trace.user_id,
            session_id=trace.session_id,
            turn_id=trace.turn_id,
            **data,
        )
        db.add(record)

    for tool_span in trace.tool_spans:
        tool_data = tool_span.finish()
        tool_record = ToolTrace(
            user_id=trace.user_id,
            session_id=trace.session_id,
            turn_id=trace.turn_id,
            **tool_data,
        )
        db.add(tool_record)

    await db.flush()
