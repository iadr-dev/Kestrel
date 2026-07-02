"""Skill matcher — keyword matching + LLM fallback for ambiguous intents."""

from pathlib import Path

from app.agent.router import LLMRouter
from app.agent.skills.registry import SkillDefinition, SkillRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "skill_matcher.md"
MATCH_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else "Match skill for: {message}"


class SkillMatcher:
    """Two-phase skill matching: keyword → LLM fallback."""

    def __init__(self, registry: SkillRegistry, router: LLMRouter | None = None) -> None:
        self._registry = registry
        self._router = router

    def match(self, user_input: str) -> SkillDefinition | None:
        """Phase 1: keyword matching (fast, no LLM cost)."""
        return self._registry.match(user_input)

    async def match_with_llm(self, user_input: str) -> SkillDefinition | None:
        """Phase 2: LLM-based matching when keywords miss (costs ~100 tokens)."""
        # First try keywords
        result = self.match(user_input)
        if result:
            return result

        # LLM fallback
        if not self._router:
            return None

        catalog = self._registry.get_catalog()
        if not catalog:
            return None

        skill_list = "\n".join(f"- {s.name}: {s.description}" for s in catalog)
        prompt = MATCH_PROMPT.format(skill_list=skill_list, message=user_input[:200])

        try:
            response = await self._router.call(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
            )
            skill_name = response.text.strip().lower()
            if skill_name != "none":
                for s in catalog:
                    if s.name == skill_name:
                        logger.info("skill_matched_by_llm", skill=skill_name, input=user_input[:50])
                        return s
        except Exception as e:
            logger.debug("llm_skill_match_failed", error=str(e))

        return None
