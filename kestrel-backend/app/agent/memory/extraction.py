"""Post-turn fact extraction — learns user preferences/patterns asynchronously."""

from pathlib import Path

from app.agent.router import LLMRouter
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "fact_extraction.md"
EXTRACTION_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else "Extract facts from: {user_message}"


async def extract_facts(
    user_message: str,
    agent_response: str,
    router: LLMRouter,
) -> list[dict[str, str | float]]:
    """Extract user facts from a conversation turn. Non-blocking, best-effort."""
    try:
        import json
        # NOTE: use .replace(), NOT .format() — the prompt body contains literal JSON
        # examples ({"type": ...}) that str.format() would parse as format fields and
        # raise KeyError. (This previously made fact extraction fail on every turn.)
        prompt = (
            EXTRACTION_PROMPT
            .replace("{user_message}", user_message[:300])
            .replace("{response_summary}", agent_response[:200])
        )
        response = await router.call(
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        text = response.text.strip()
        # Strip markdown code fences some models wrap JSON in.
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if not text:
            return []
        facts = json.loads(text)
        if isinstance(facts, list):
            return [f for f in facts if isinstance(f, dict) and "key" in f and "value" in f]
    except Exception as e:
        logger.debug("fact_extraction_failed", error=str(e))
    return []
