"""Base tool protocol — all agent tools implement this."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolResult:
    content: str
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    error: str | None = None
    display_name: str | None = None


class BaseTool(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def parameters(self) -> dict[str, Any]: ...

    async def execute(self, args: dict[str, Any]) -> ToolResult: ...

    @property
    def display_name_template(self) -> str:
        """Human-friendly template: '查詢{stock_id}股價' → '查詢2330股價'"""
        ...
