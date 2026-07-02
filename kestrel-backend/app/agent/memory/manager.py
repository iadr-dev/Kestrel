"""MemoryManager — unified interface over all 4 memory layers."""

from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.memory.compression import ContextCompactor
from app.agent.memory.episodic import EpisodicMemory
from app.agent.memory.extraction import extract_facts
from app.agent.memory.semantic import SemanticMemory
from app.agent.memory.working import WorkingMemory
from app.agent.router import LLMRouter
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Orchestrates working + episodic + semantic memory with auto-compression."""

    def __init__(self, session: AsyncSession, user_id: str, session_id: str | None = None) -> None:
        self._user_id = user_id
        self._session_id = session_id or str(uuid4())
        self._turn_index = 0
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory(session, user_id)
        self.semantic = SemanticMemory(session, user_id)
        self._compactor = ContextCompactor()

    @property
    def session_id(self) -> str:
        return self._session_id

    async def build_context(self, query: str) -> dict[str, Any]:
        """
        Assemble full context for LLM call:
        1. Semantic facts (user preferences/goals)
        2. Relevant past conversations (episodic search)
        3. Current working memory turns
        """
        semantic_context = await self.semantic.get_context_summary()

        relevant_past = await self.episodic.search(query, limit=3)
        past_context = ""
        if relevant_past:
            past_lines = [f"[{t.role}] {t.content[:200]}" for t in relevant_past[:3]]
            past_context = "[Relevant past conversations]\n" + "\n".join(past_lines)

        return {
            "semantic": semantic_context,
            "past": past_context,
            "working_messages": self.working.get_messages(),
            "token_count": self.working.token_count,
        }

    async def record_turn(
        self, role: str, content: str, metadata: dict[str, Any] | None = None, turn_id: str | None = None
    ) -> None:
        """Save turn to both working memory and episodic storage.

        `turn_id` lets the caller persist the assistant turn under the id the client
        sees (done event's turn_id) so feedback/retry/edit can look it up.
        """
        self.working.add_turn(role, content, metadata)
        await self.episodic.save_turn(
            session_id=self._session_id,
            role=role,
            content=content,
            turn_index=self._turn_index,
            metadata=metadata,
            turn_id=turn_id,
        )
        self._turn_index += 1

    async def maybe_compress(self, router: LLMRouter) -> bool:
        """Compress working memory if over budget."""
        return await self._compactor.maybe_compact(self.working, router)

    async def extract_and_learn(self, user_message: str, agent_response: str, router: LLMRouter) -> None:
        """Post-turn: extract facts from conversation and store in semantic memory."""
        facts = await extract_facts(user_message, agent_response, router)
        for fact in facts:
            await self.semantic.learn_fact(
                fact_type=str(fact.get("type", "pattern")),
                fact_key=str(fact["key"]),
                fact_value=str(fact["value"]),
                confidence=float(fact.get("confidence", 0.7)),
                source_session=self._session_id,
            )
        if facts:
            logger.info("facts_learned", count=len(facts), user_id=self._user_id)

    async def get_session_history(self) -> list[dict[str, str]]:
        """Load full session history from episodic memory."""
        turns = await self.episodic.get_session_turns(self._session_id)
        return [{"role": t.role, "content": t.content} for t in turns]
