"""Agent session endpoints — list, detail, delete, resume."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.agent import (
    SessionDetailResponse,
    SessionListResponse,
    SessionResumeResponse,
)
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """List user's chat sessions."""
    from app.agent.sessions.repository import SessionRepository
    repo = SessionRepository(db, user_id=user_id)
    sessions = await repo.list_recent(limit=50)
    return {
        "data": [
            {
                "id": s.id,
                "title": s.title,
                "turn_count": s.turn_count,
                "last_message": s.last_message_preview,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
        "count": len(sessions),
    }


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Load session conversation history."""
    from app.agent.memory.episodic import EpisodicMemory
    memory = EpisodicMemory(db, user_id=user_id)
    turns = await memory.get_session_turns(session_id)

    import json as _json

    def _turn_dict(t: Any) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if t.metadata_json:
            try:
                meta = _json.loads(t.metadata_json) if isinstance(t.metadata_json, str) else (t.metadata_json or {})
            except Exception:
                meta = {}
        return {
            "id": t.id,
            "role": t.role,
            "content": t.content,
            "turn_index": t.turn_index,
            "created_at": t.created_at.isoformat(),
            # Restore the full timeline on reopen (assistant turns carry these).
            "thinking": meta.get("thinking"),
            "tools": meta.get("tools"),
        }

    return {
        "session_id": session_id,
        "turns": [_turn_dict(t) for t in turns],
        "count": len(turns),
    }


@router.delete("/sessions/{session_id}", response_model=StatusResponse)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Delete a session and all its turns."""
    from app.agent.memory.episodic import EpisodicMemory
    from app.agent.sessions.repository import SessionRepository
    memory = EpisodicMemory(db, user_id=user_id)
    repo = SessionRepository(db, user_id=user_id)
    await memory.delete_session(session_id)
    await repo.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/resume", response_model=SessionResumeResponse)
async def resume_session(session_id: str, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Resume a previous session — returns handoff summary for context."""
    from app.agent.sessions.repository import SessionRepository
    repo = SessionRepository(db, user_id=user_id)
    session = await repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(message="Session not found")
    return {
        "status": "resumed",
        "session_id": session_id,
        "title": session.title,
        "handoff_summary": session.handoff_summary,
        "turn_count": session.turn_count,
    }
