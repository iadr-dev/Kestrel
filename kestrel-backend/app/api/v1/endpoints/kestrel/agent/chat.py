"""Agent chat endpoints — streaming SSE, non-streaming, feedback, retry, edit, clarify."""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import AgentService
from app.agent.events import event_to_dict, serialize_event
from app.core.exceptions import NotFoundError, RateLimitError, ValidationError
from app.core.logging import get_logger
from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.agent import ChatResponse, FeedbackResponse

from ._common import (
    ChatRequest,
    EditRequest,
    FeedbackRequest,
    RetryRequest,
    cost_tracker,
    get_agent_service,
    quality_tracker,
    sse_error,
)

router = APIRouter(prefix="/agent", tags=["Agent"])
logger = get_logger(__name__)

_SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


@router.post("/chat/stream")
async def agent_chat_stream(
    request: ChatRequest,
    http_request: Request,
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """SSE streaming agent chat."""
    error = request.validate_message()
    if error:
        raise ValidationError(message=error)

    # Check chat limit by tier (BYOK removes the cap — user pays their own inference).
    from app.agent.hooks.tier_gate import TierGate
    from app.core.exceptions import TierInsufficientError
    from app.dependencies import get_user_tier_and_keys
    try:
        user_tier, has_user_keys = await get_user_tier_and_keys(db, user_id)
        chats_today = cost_tracker._get_counter(user_id).call_count
        TierGate().check_chat_limit(user_tier, chats_today, has_user_keys=has_user_keys)
    except TierInsufficientError as e:
        raise RateLimitError(message=str(e), error_code="CHAT_LIMIT") from e
    except Exception:
        pass  # Don't block chat if tier check fails

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # Determine extra tools based on features
            # web_search: enables ad-hoc single searches + page reading
            # research: enables deep multi-angle research (implies web access)
            extra_tools: list[str] | None = None
            if request.features:
                extra_tools = []
                if request.features.web_search or request.features.research:
                    extra_tools.extend(["web_search", "fetch_page"])
                if request.features.research:
                    extra_tools.append("deep_research")

            async for event in service.process_stream(
                user_message=request.message.strip(),
                session_id=request.session_id,
                db_session=db,
                model=request.model,
                user_id=user_id,
                extra_tools=extra_tools,
                locale=request.locale or "zh-TW",
                attachments=request.attachments,
                plan_mode=bool(request.features and request.features.plan),
            ):
                # Stop server-side work the moment the client goes away (Stop button
                # aborts the fetch → disconnect). Breaking closes this generator,
                # which propagates GeneratorExit up through process_stream → the agent
                # loop, cancelling further LLM calls / tool runs instead of burning
                # tokens on an abandoned turn.
                if await http_request.is_disconnected():
                    logger.info("agent_stream_client_disconnected", user_id=user_id)
                    break
                yield serialize_event(event)
        except Exception as e:
            yield sse_error(e)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Non-streaming agent chat."""
    error = request.validate_message()
    if error:
        raise ValidationError(message=error)

    events = []
    text_parts = []
    async for event in service.process_stream(
        user_message=request.message.strip(),
        session_id=request.session_id,
        db_session=db,
        user_id=user_id,
    ):
        events.append(event)
        if hasattr(event, "delta"):
            text_parts.append(event.delta)

    return {"response": "".join(text_parts), "events": [event_to_dict(e) for e in events]}


@router.post("/chat/feedback", response_model=FeedbackResponse)
async def agent_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Store thumb up/down — persists to DB, triggers quality alerts if needed."""
    from sqlalchemy import select

    from app.agent.hooks.feedback_loop import FeedbackService
    from app.agent.observe import LLMTrace

    # Resolve skill_name from turn trace if not provided by frontend
    skill_name = request.skill_name
    if not skill_name and request.turn_id:
        try:
            stmt = select(LLMTrace).where(LLMTrace.turn_id == request.turn_id)
            result = await db.execute(stmt)
            trace = result.scalar_one_or_none()
            if trace and hasattr(trace, "metadata_json") and trace.metadata_json:
                import json as json_mod
                meta = json_mod.loads(trace.metadata_json) if isinstance(trace.metadata_json, str) else {}
                skill_name = meta.get("skill_name")
        except Exception:
            pass

    # Persist to DB via FeedbackService (rolling window, alerts)
    svc = FeedbackService(db)
    await svc.record(
        user_id=user_id,
        turn_id=request.turn_id,
        rating=request.rating,
        skill_name=skill_name,
        comment=request.comment,
    )

    # Also update in-memory tracker (for real-time quality in core.py)
    quality_tracker.record_feedback(skill_name, request.rating)

    # Get current quality score
    quality = await svc.get_skill_quality(skill_name) if skill_name else None

    return {
        "status": "recorded",
        "turn_id": request.turn_id,
        "rating": request.rating,
        "skill_name": skill_name,
        "skill_quality": quality.get("score") if quality else None,
    }


@router.post("/chat/retry")
async def agent_retry(
    request: RetryRequest,
    http_request: Request,
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """Re-generate response for a turn — looks up original message and re-runs."""
    from sqlalchemy import select

    from app.agent.memory.episodic import ConversationTurn

    # Find the user turn that preceded this assistant turn (scoped to the caller).
    stmt = (
        select(ConversationTurn)
        .where(
            ConversationTurn.id == request.turn_id,
            ConversationTurn.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    turn = result.scalar_one_or_none()

    if not turn:
        raise NotFoundError(message="Turn not found")

    # Find the user message before this turn
    stmt = (
        select(ConversationTurn)
        .where(
            ConversationTurn.session_id == turn.session_id,
            ConversationTurn.role == "user",
            ConversationTurn.turn_index < turn.turn_index,
        )
        .order_by(ConversationTurn.turn_index.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    user_turn = result.scalar_one_or_none()
    original_message = user_turn.content if user_turn else turn.content

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in service.process_stream(
                user_message=original_message,
                session_id=turn.session_id,
                db_session=db,
            ):
                if await http_request.is_disconnected():
                    break
                yield serialize_event(event)
        except Exception as e:
            yield sse_error(e)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/edit")
async def agent_edit(
    request: EditRequest,
    http_request: Request,
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """Edit user message and re-run from that point (truncates later turns)."""
    from sqlalchemy import delete, select

    from app.agent.memory.episodic import ConversationTurn

    # Truncate turns after the edited one (scoped to the caller).
    stmt = select(ConversationTurn).where(
        ConversationTurn.id == request.turn_id,
        ConversationTurn.user_id == user_id,
    )
    result = await db.execute(stmt)
    turn = result.scalar_one_or_none()

    if turn:
        del_stmt = delete(ConversationTurn).where(
            ConversationTurn.user_id == user_id,
            ConversationTurn.session_id == turn.session_id,
            ConversationTurn.turn_index >= turn.turn_index,
        )
        await db.execute(del_stmt)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in service.process_stream(
                user_message=request.new_message.strip(),
                session_id=turn.session_id if turn else request.session_id,
                db_session=db,
            ):
                if await http_request.is_disconnected():
                    break
                yield serialize_event(event)
        except Exception as e:
            yield sse_error(e)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/clarify")
async def agent_clarify(
    http_request: Request,
    request: dict[str, Any] = Body(default_factory=dict),
    service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """Resume agent loop after ask_user pause — provide the user's answer to a clarification question.

    Body: {"session_id": "...", "clarification_id": "...", "answer": "user's choice or text"}
    """
    session_id = request.get("session_id")
    answer = request.get("answer", "")
    clarification_id = request.get("clarification_id", "")

    resume_message = f"[User answered clarification {clarification_id}]: {answer}"

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in service.process_stream(
                user_message=resume_message,
                session_id=session_id,
                db_session=db,
                user_id=user_id,
            ):
                if await http_request.is_disconnected():
                    break
                yield serialize_event(event)
        except Exception as e:
            yield sse_error(e)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
