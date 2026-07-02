"""Layer 4: Context Compaction — auto-summarize when token budget exceeded."""

from pathlib import Path

from app.agent.memory.working import WorkingMemory
from app.agent.router import LLMRouter
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "context_summary.md"
COMPRESSION_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else "Summarize this conversation concisely."


class ContextCompactor:
    MAX_WORKING_TOKENS = 50_000
    KEEP_RECENT_TURNS = 6

    async def maybe_compact(self, working: WorkingMemory, router: LLMRouter) -> bool:
        """Auto-compress if token budget exceeded. Returns True if compaction happened."""
        if not working.needs_compression:
            return False

        old_turns, recent_turns = working.split_for_compression()
        if not old_turns:
            return False

        old_text = "\n".join(
            f"[{t.role}]: {t.content[:500]}" for t in old_turns
        )

        logger.info(
            "context_compacting",
            old_turns=len(old_turns),
            recent_turns=len(recent_turns),
            token_count=working.token_count,
        )

        try:
            response = await router.call(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": f"{COMPRESSION_PROMPT}\n\n{old_text}"}],
                max_tokens=500,
            )
            working.replace_with_summary(response.text, recent_turns)
            logger.info("context_compacted", new_token_count=working.token_count)
            return True
        except Exception as e:
            logger.error("compression_failed", error=str(e))
            return False
