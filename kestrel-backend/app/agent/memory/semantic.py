"""Layer 3: Semantic Memory — long-term facts about the user (preferences, goals, patterns)."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class SemanticFact(Base):
    __tablename__ = "semantic_facts"
    __table_args__ = (
        Index("ix_semantic_user_type", "user_id", "fact_type"),
        Index("ix_semantic_user_key", "user_id", "fact_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    fact_type: Mapped[str] = mapped_column(String(50))
    fact_key: Mapped[str] = mapped_column(String(200))
    fact_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    source_session: Mapped[str | None] = mapped_column(String(36))
    is_user_set: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SemanticMemory:
    """Structured facts about the user for personalization."""

    FACT_TYPES = ("preference", "history", "pattern", "goal", "portfolio")

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._session = session
        self._user_id = user_id

    async def learn_fact(
        self,
        fact_type: str,
        fact_key: str,
        fact_value: str,
        confidence: float = 0.8,
        source_session: str | None = None,
        is_user_set: bool = False,
    ) -> None:
        """Upsert a fact — update if same (type, key) exists, insert otherwise.

        Facts are scoped by ``(user_id, fact_type, fact_key)``: the same key
        (e.g. ``market_preference``) can live under different fact types
        (``ui_preferences`` vs ``agent_settings``) without clobbering. A
        user-set fact is sticky — a later non-user write (e.g. the background
        LLM extractor) will not overwrite a value the user chose deliberately.
        """
        existing = await self._get_by_key(fact_type, fact_key)
        if existing:
            if existing.is_user_set and not is_user_set:
                # Protect a deliberate user choice from automated overwrites.
                return
            existing.fact_value = fact_value
            existing.confidence = max(existing.confidence, confidence)
            existing.updated_at = datetime.now(UTC)
            if is_user_set:
                existing.is_user_set = True
        else:
            fact = SemanticFact(
                user_id=self._user_id,
                fact_type=fact_type,
                fact_key=fact_key,
                fact_value=fact_value,
                confidence=confidence,
                source_session=source_session,
                is_user_set=is_user_set,
            )
            self._session.add(fact)
        await self._session.flush()

    async def get_all_facts(self) -> Sequence[SemanticFact]:
        stmt = (
            select(SemanticFact)
            .where(SemanticFact.user_id == self._user_id)
            .order_by(SemanticFact.fact_type, SemanticFact.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_facts_by_type(self, fact_type: str) -> Sequence[SemanticFact]:
        stmt = (
            select(SemanticFact)
            .where(SemanticFact.user_id == self._user_id, SemanticFact.fact_type == fact_type)
            .order_by(SemanticFact.confidence.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_context_summary(self) -> str:
        """Build a compact text summary for injection into system prompt."""
        facts = await self.get_all_facts()
        if not facts:
            return ""
        lines = ["[User Profile]"]
        for fact in facts:
            lines.append(f"- [{fact.fact_type}] {fact.fact_key}: {fact.fact_value}")
        return "\n".join(lines)

    async def forget_fact(self, fact_id: str) -> bool:
        fact = await self._session.get(SemanticFact, fact_id)
        if fact and fact.user_id == self._user_id:
            await self._session.delete(fact)
            await self._session.flush()
            return True
        return False

    async def forget_fact_by_key(self, fact_type: str, fact_key: str) -> bool:
        """Delete a fact by its (type, key) for this user. Returns True if removed."""
        fact = await self._get_by_key(fact_type, fact_key)
        if fact:
            await self._session.delete(fact)
            await self._session.flush()
            return True
        return False

    async def _get_by_key(self, fact_type: str, fact_key: str) -> SemanticFact | None:
        stmt = (
            select(SemanticFact)
            .where(
                SemanticFact.user_id == self._user_id,
                SemanticFact.fact_type == fact_type,
                SemanticFact.fact_key == fact_key,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
