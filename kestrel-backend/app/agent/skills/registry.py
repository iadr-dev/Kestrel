"""Skill Registry — L1/L2/L3 progressive loading for token efficiency.

L1 (catalog): name + description (50-100 tokens each) — always in system prompt
L2 (activation): full instructions + tool list — loaded when skill triggers
L3 (resources): reference docs — loaded on-demand during execution
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SkillDefinition:
    """L1 — always in context. ~50-100 tokens per skill."""
    name: str
    description: str
    tier: str = "free"
    design_pattern: str = "tool_wrapper"


@dataclass
class SkillBody:
    """L2 — loaded when skill is triggered."""
    system_instructions: str
    tools: list[str] = field(default_factory=list)
    output_format: str = "text"
    # Optional governance fields (borrowed from the Hermes role design): a defined
    # output section structure, a role-tuned data-freshness rule, and scope boundaries.
    # All optional + backward-compatible; composed into the effective prompt by
    # `effective_instructions()`.
    output_structure: list[str] = field(default_factory=list)
    freshness_rule: str = ""
    boundaries: list[str] = field(default_factory=list)

    def effective_instructions(self) -> str:
        """Instructions + (when present) 輸出結構 / 資料時效 / 邊界限制 appended as a
        consistent governance footer, so every skill emits a predictable shape."""
        parts = [self.system_instructions.rstrip()]
        if self.output_structure:
            parts.append("輸出結構（務必依此順序輸出對應段落）:\n" + "\n".join(f"- {s}" for s in self.output_structure))
        if self.freshness_rule:
            parts.append(f"資料時效要求: {self.freshness_rule}")
        if self.boundaries:
            parts.append("邊界限制（嚴格遵守，不可逾越）:\n" + "\n".join(f"- {b}" for b in self.boundaries))
        return "\n\n".join(p for p in parts if p.strip())


@dataclass
class SkillResources:
    """L3 — loaded on demand during execution."""
    reference_docs: list[str] = field(default_factory=list)


class SkillRegistry:
    def __init__(self, catalog_dir: str | Path | None = None) -> None:
        self._catalog_dir = Path(catalog_dir) if catalog_dir else Path(__file__).parent / "catalog"
        self._skills: dict[str, dict[str, Any]] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self._catalog_dir.exists():
            logger.warning("skills_catalog_missing", path=str(self._catalog_dir))
            return

        for file in sorted(self._catalog_dir.glob("*.yaml")):
            try:
                with open(file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict) and "name" in data:
                    self._skills[data["name"]] = data
                    logger.debug("skill_loaded", name=data["name"])
            except Exception as e:
                logger.error("skill_load_error", file=str(file), error=str(e))

        logger.info("skills_catalog_loaded", count=len(self._skills))

    def get_catalog(self) -> list[SkillDefinition]:
        """L1: Returns all skill definitions for system prompt injection."""
        return [
            SkillDefinition(
                name=s["name"],
                description=s.get("description", ""),
                tier=s.get("tier", "free"),
                design_pattern=s.get("design_pattern", "tool_wrapper"),
            )
            for s in self._skills.values()
        ]

    def get_catalog_prompt(self) -> str:
        """Format L1 catalog as text for system prompt."""
        catalog = self.get_catalog()
        if not catalog:
            return ""
        lines = ["[Available Skills]"]
        for skill in catalog:
            lines.append(f"- {skill.name}: {skill.description}")
        return "\n".join(lines)

    def match(self, user_input: str, detected_intent: str | None = None) -> SkillDefinition | None:
        """Match user input to a skill based on description triggers."""
        input_lower = user_input.lower()
        for data in self._skills.values():
            triggers = data.get("triggers", [])
            for trigger in triggers:
                if trigger.lower() in input_lower:
                    return SkillDefinition(
                        name=data["name"],
                        description=data.get("description", ""),
                        tier=data.get("tier", "free"),
                        design_pattern=data.get("design_pattern", "tool_wrapper"),
                    )
        return None

    def load_body(self, skill_name: str) -> SkillBody | None:
        """L2: Load full instructions when skill is activated."""
        data = self._skills.get(skill_name)
        if not data:
            return None
        return SkillBody(
            system_instructions=data.get("instructions", ""),
            tools=data.get("tools", []),
            output_format=data.get("output_format", "text"),
            output_structure=data.get("output_structure", []),
            freshness_rule=data.get("freshness_rule", ""),
            boundaries=data.get("boundaries", []),
        )

    def load_resources(self, skill_name: str) -> SkillResources | None:
        """L3: Load reference docs on demand."""
        data = self._skills.get(skill_name)
        if not data:
            return None
        return SkillResources(
            reference_docs=data.get("resources", []),
        )

    @property
    def skill_count(self) -> int:
        return len(self._skills)
