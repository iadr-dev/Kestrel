"""Agent semantic-memory endpoints — list, update, delete facts."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_session
from app.dependencies import get_current_user_id
from app.schemas.agent import MemoryListResponse, MemoryUpdateResponse
from app.schemas.common import StatusResponse

from ._common import MemoryUpdateRequest

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/memory", response_model=MemoryListResponse)
async def get_memory(db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get user's semantic facts."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id=user_id)
    facts = await memory.get_all_facts()
    return {
        "data": [
            {
                "id": f.id,
                "type": f.fact_type,
                "key": f.fact_key,
                "value": f.fact_value,
                "confidence": f.confidence,
                "is_user_set": f.is_user_set,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in facts
        ],
        "count": len(facts),
    }


@router.put("/memory/{fact_id}", response_model=MemoryUpdateResponse)
async def update_memory(
    fact_id: str,
    request: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Update a semantic fact (user correction)."""
    from app.agent.memory.semantic import SemanticFact
    fact = await db.get(SemanticFact, fact_id)
    if not fact or fact.user_id != user_id:
        raise NotFoundError(message="Fact not found")
    fact.fact_value = request.fact_value
    if request.confidence is not None:
        fact.confidence = request.confidence
    fact.is_user_set = True
    return {"status": "updated", "fact_id": fact_id, "new_value": request.fact_value}


@router.delete("/memory/{fact_id}", response_model=StatusResponse)
async def delete_memory(fact_id: str, db: AsyncSession = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    """Forget a semantic fact."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id=user_id)
    deleted = await memory.forget_fact(fact_id)
    if not deleted:
        raise NotFoundError(message="Fact not found")
    return {"status": "deleted", "fact_id": fact_id}
