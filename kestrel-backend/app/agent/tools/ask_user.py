"""ask_user tool — pauses the agent loop to request clarification from the user."""

from typing import Any
from uuid import uuid4

from app.agent.tools.base import ToolResult


class AskUserTool:
    name = "ask_user"
    description = "Ask the user a clarifying question when you need more information to proceed. Provide options when possible."
    display_name_template = "詢問使用者"
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask the user"},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices for the user to pick from",
            },
        },
        "required": ["question"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        question = args.get("question", "")
        options = args.get("options", [])
        clarification_id = str(uuid4())
        return ToolResult(
            content=f"[PAUSE] Waiting for user response: {question}",
            data={
                "type": "ask_user",
                "question": question,
                "options": options,
                "clarification_id": clarification_id,
            },
        )
