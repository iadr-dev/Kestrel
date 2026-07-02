"""Skill loader — handles file I/O and resource loading for L3."""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.core.logging import get_logger

logger = get_logger(__name__)


class SkillLoader:
    """Loads skill definitions from YAML files and resources from disk."""

    def __init__(self, catalog_dir: Path) -> None:
        self._catalog_dir = catalog_dir

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all YAML skill files from catalog directory."""
        skills: dict[str, dict[str, Any]] = {}
        if not self._catalog_dir.exists():
            return skills

        for file in sorted(self._catalog_dir.glob("*.yaml")):
            try:
                with open(file) as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict) and "name" in data:
                    skills[data["name"]] = data
            except Exception as e:
                logger.error("skill_file_error", file=str(file), error=str(e))

        return skills

    def load_resource(self, resource_path: str, base_dir: Path | None = None) -> str | None:
        """Load L3 resource content from a file path."""
        if base_dir:
            full_path = base_dir / resource_path
        else:
            full_path = Path(resource_path)

        if not full_path.exists():
            logger.warning("resource_not_found", path=str(full_path))
            return None

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("resource_load_error", path=str(full_path), error=str(e))
            return None

    def load_resources_for_skill(self, skill_data: dict[str, Any], base_dir: Path | None = None) -> list[str]:
        """Load all L3 resources for a skill."""
        resource_paths = skill_data.get("resources", [])
        contents: list[str] = []
        for path in resource_paths:
            content = self.load_resource(path, base_dir)
            if content:
                contents.append(content)
        return contents
