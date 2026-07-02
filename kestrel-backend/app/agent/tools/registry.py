"""Central tool registry — maps tool names to executors and provides schemas."""

import time
from typing import Any

from app.agent.tools.base import BaseTool, ToolResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get_schemas(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for LLM calls."""
        tools = self._tools.values() if names is None else [
            self._tools[n] for n in names if n in self._tools
        ]
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    async def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(content="", error=f"Unknown tool: {name}")

        start = time.perf_counter()
        try:
            result = await tool.execute(args)
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.debug("tool_executed", tool=name, duration_ms=duration_ms)
            return result
        except Exception as e:
            logger.error("tool_error", tool=name, error=str(e))
            return ToolResult(content="", error=str(e))

    def get_display_name(self, tool_name: str, args: dict[str, Any]) -> str:
        """Generate human-friendly display name for UI."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return tool_name
        template = getattr(tool, "display_name_template", tool_name)
        try:
            return template.format(**args)
        except (KeyError, IndexError):
            return template

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name (used by subagent framework)."""
        return self._tools.get(name)

    @property
    def available_tools(self) -> list[str]:
        return list(self._tools.keys())
