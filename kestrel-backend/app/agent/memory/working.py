"""Layer 1: Working Memory — in-context turns with token budget management."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    role: str
    content: str
    is_summary: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """Token-budgeted conversation buffer. Oldest turns get compressed when budget exceeded."""

    CHARS_PER_TOKEN = 3.5
    MAX_TOKENS = 50_000
    KEEP_RECENT = 6

    def __init__(self, max_tokens: int = 50_000) -> None:
        self.MAX_TOKENS = max_tokens
        self._turns: list[Turn] = []

    def add_turn(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._turns.append(Turn(role=role, content=content, metadata=metadata or {}))

    def get_messages(self) -> list[dict[str, str]]:
        """Return turns as LLM-compatible messages."""
        return [{"role": t.role, "content": t.content} for t in self._turns]

    @property
    def token_count(self) -> int:
        total_chars = sum(len(t.content) for t in self._turns)
        return int(total_chars / self.CHARS_PER_TOKEN)

    @property
    def needs_compression(self) -> bool:
        return self.token_count > self.MAX_TOKENS

    def split_for_compression(self) -> tuple[list[Turn], list[Turn]]:
        """Split into old turns (to compress) and recent turns (to keep verbatim)."""
        if len(self._turns) <= self.KEEP_RECENT:
            return [], self._turns[:]
        split_point = len(self._turns) - self.KEEP_RECENT
        return self._turns[:split_point], self._turns[split_point:]

    def replace_with_summary(self, summary: str, recent_turns: list[Turn]) -> None:
        """Replace old turns with a compressed summary + keep recent verbatim."""
        summary_turn = Turn(
            role="system",
            content=f"[Previous conversation summary]\n{summary}",
            is_summary=True,
        )
        self._turns = [summary_turn] + recent_turns

    def clear(self) -> None:
        self._turns.clear()

    @property
    def turn_count(self) -> int:
        return len(self._turns)
