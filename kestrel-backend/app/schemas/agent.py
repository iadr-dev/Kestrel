from typing import Any

from pydantic import BaseModel, Field

# --- Request Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str | None = None


class FeedbackRequest(BaseModel):
    turn_id: str
    rating: str
    skill_name: str | None = None
    comment: str | None = None


class RetryRequest(BaseModel):
    session_id: str
    turn_index: int | None = None


class EditRequest(BaseModel):
    session_id: str
    turn_index: int
    new_message: str


class ClarifyRequest(BaseModel):
    session_id: str
    clarification: str


class MemoryUpdateRequest(BaseModel):
    value: str


class AlertCreateRequest(BaseModel):
    stock_id: str
    condition: str
    threshold: float | None = None
    message: str | None = None


# --- Response Models ---

class ChatResponse(BaseModel):
    response: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackResponse(BaseModel):
    status: str
    turn_id: str
    rating: str
    skill_name: str | None = None
    skill_quality: float | None = None


class SessionItem(BaseModel):
    id: str
    title: str | None = None
    turn_count: int = 0
    last_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SessionListResponse(BaseModel):
    data: list[SessionItem] = Field(default_factory=list)
    count: int = 0


class SessionTurn(BaseModel):
    id: str | None = None
    role: str
    content: str
    turn_index: int
    created_at: str | None = None
    # Assistant turns restore their reasoning + tool timeline when a chat is reopened.
    thinking: str | None = None
    tools: list[dict[str, Any]] | None = None


class SessionDetailResponse(BaseModel):
    session_id: str
    turns: list[SessionTurn] = Field(default_factory=list)
    count: int = 0


class SessionResumeResponse(BaseModel):
    status: str
    session_id: str
    title: str | None = None
    handoff_summary: str | None = None
    turn_count: int = 0


class MemoryFact(BaseModel):
    id: str
    type: str | None = None
    key: str | None = None
    value: str | None = None
    confidence: float | None = None
    is_user_set: bool = False
    created_at: str | None = None


class MemoryListResponse(BaseModel):
    data: list[MemoryFact] = Field(default_factory=list)
    count: int = 0


class MemoryUpdateResponse(BaseModel):
    status: str
    fact_id: str
    new_value: str


class AgentAlert(BaseModel):
    id: str
    stock_id: str | None = None
    condition: str | None = None
    threshold: float | None = None
    message: str | None = None
    is_active: bool = True
    created_at: str | None = None


class AgentAlertListResponse(BaseModel):
    data: list[AgentAlert] = Field(default_factory=list)
    count: int = 0


class AgentAlertCreateResponse(BaseModel):
    status: str
    alert: AgentAlert


class SkillInfo(BaseModel):
    name: str
    description: str | None = None
    tier: str | None = None
    pattern: str | None = None
    quality_score: float | None = None


class SkillListResponse(BaseModel):
    data: list[SkillInfo] = Field(default_factory=list)
    count: int = 0


class CostResponse(BaseModel):
    daily_cost_usd: float = 0.0
    calls_today: int = 0
    budget_ok: bool = True
    tier: str = "free"


class QualityResponse(BaseModel):
    skills: list[dict[str, Any]] = Field(default_factory=list)
    window_days: int = 7


class FeedbackAlertItem(BaseModel):
    id: str
    skill_name: str | None = None
    quality_score: float | None = None
    sample_count: int = 0
    status: str = "pending"
    resolved_by: str | None = None
    resolved_at: str | None = None
    resolution_note: str | None = None
    created_at: str | None = None


class FeedbackAlertListResponse(BaseModel):
    data: list[FeedbackAlertItem] = Field(default_factory=list)
    count: int = 0


class FeedbackEventItem(BaseModel):
    id: str
    user_id: str | None = None
    turn_id: str | None = None
    skill_name: str | None = None
    rating: str | None = None
    comment: str | None = None
    model_used: str | None = None
    created_at: str | None = None


class FeedbackRecentResponse(BaseModel):
    data: list[FeedbackEventItem] = Field(default_factory=list)
    count: int = 0
