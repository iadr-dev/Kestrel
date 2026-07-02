"""Shared request models, singletons, and helpers for the agent routers.

Split out of the former monolithic agent.py so the chat/sessions/memory/alerts/
insights routers can share these without circular imports.
"""

from typing import Any

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import AgentService
from app.agent.hooks.cost_tracker import CostTracker
from app.agent.hooks.feedback_loop import get_quality_tracker
from app.core.constants import MAX_CHAT_MESSAGE_LENGTH
from app.db.session import get_session
from app.dependencies import get_current_user_id

# Process-wide singletons (in production these could move to app.state).
cost_tracker = CostTracker()
quality_tracker = get_quality_tracker()


# --- Request models ---


class ChatFeatures(BaseModel):
    web_search: bool = False
    research: bool = False
    # Plan mode: the agent outlines a step-by-step plan and STOPS (no tool execution)
    # so the user can review/approve before it runs.
    plan: bool = False


class Attachment(BaseModel):
    """A user-uploaded file. Images are sent to a vision model; text-based docs
    (csv/json/txt) are decoded and injected as context. `data_url` is a base64
    data URI as produced by the browser's FileReader.readAsDataURL."""

    name: str
    type: str  # MIME type, e.g. "image/png", "text/csv", "application/pdf"
    data_url: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str | None = None
    features: ChatFeatures | None = None
    locale: str | None = None
    attachments: list[Attachment] | None = None

    def validate_message(self) -> str | None:
        if not self.message or not self.message.strip():
            return "Message cannot be empty"
        if len(self.message) > MAX_CHAT_MESSAGE_LENGTH:
            return f"Message too long (max {MAX_CHAT_MESSAGE_LENGTH} characters)"
        return None


class FeedbackRequest(BaseModel):
    turn_id: str
    rating: str
    comment: str | None = None
    skill_name: str | None = None


class RetryRequest(BaseModel):
    turn_id: str
    session_id: str | None = None


class EditRequest(BaseModel):
    turn_id: str
    new_message: str
    session_id: str | None = None


class AlertCreateRequest(BaseModel):
    stock_id: str
    condition: str
    threshold: float
    message: str | None = None


class MemoryUpdateRequest(BaseModel):
    fact_value: str
    confidence: float | None = None


# --- Shared dependencies ---


async def get_agent_service(request: Request) -> AgentService:
    service: AgentService = request.app.state.agent_service
    return service


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> str:
    from app.dependencies import is_admin_email
    from app.models.user import User
    user = await db.get(User, user_id)
    if not user or not is_admin_email(user.email):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


def sse_error(exc: Exception) -> str:
    """Format an exception as a terminal SSE error frame."""
    import json
    return f"data: {json.dumps({'type': 'error', 'message': str(exc)[:200]}, ensure_ascii=False)}\n\n"


# Re-export commonly used symbols so router modules import from one place.
__all__ = [
    "Any",
    "AgentService",
    "AsyncSession",
    "AlertCreateRequest",
    "ChatFeatures",
    "ChatRequest",
    "EditRequest",
    "FeedbackRequest",
    "MemoryUpdateRequest",
    "RetryRequest",
    "cost_tracker",
    "get_agent_service",
    "get_current_user_id",
    "get_session",
    "quality_tracker",
    "require_admin",
    "sse_error",
]
