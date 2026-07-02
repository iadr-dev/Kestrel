"""Memory tools — allow agent to explicitly recall/learn/forget facts about the user."""

from typing import Any

from app.agent.tools.base import ToolResult


class RecallContextTool:
    name = "recall_context"
    description = "Recall what you know about this user — their preferences, past analyses, holdings, goals."
    display_name_template = "回憶使用者資訊"
    parameters = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "What to recall about (e.g. 'holdings', 'preferences', 'recent stocks')"},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        topic = args.get("topic", "all")
        # Note: In the agent loop, memory context is already injected via system prompt.
        # This tool exists for explicit memory queries when the agent wants to check
        # specific facts mid-conversation (e.g., "let me check what I know about your portfolio").
        return ToolResult(
            content=f"[Memory recall '{topic}': Check the [User Profile] section in context for known facts. If empty, ask the user directly.]",
            data={"topic": topic, "source": "semantic_memory"},
        )


class LearnFactTool:
    name = "learn_fact"
    description = "Store a fact about the user (preference, holding, goal) for future reference."
    display_name_template = "記住使用者偏好"
    parameters = {
        "type": "object",
        "properties": {
            "fact_type": {
                "type": "string",
                "enum": ["preference", "portfolio", "goal", "pattern"],
                "description": "Category of fact",
            },
            "key": {"type": "string", "description": "Short identifier (e.g. 'risk_tolerance')"},
            "value": {"type": "string", "description": "The fact content"},
        },
        "required": ["fact_type", "key", "value"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        fact_type = args.get("fact_type", "preference")
        key = args.get("key", "")
        value = args.get("value", "")
        return ToolResult(
            content=f"已記住: [{fact_type}] {key} = {value}",
            data={"stored": True, "fact_type": fact_type, "key": key, "value": value},
        )


class ForgetFactTool:
    name = "forget_fact"
    description = "Remove a previously stored fact about the user."
    display_name_template = "忘記使用者資訊"
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The fact key to forget"},
        },
        "required": ["key"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        key = args.get("key", "")
        return ToolResult(
            content=f"已忘記: {key}",
            data={"forgotten": True, "key": key},
        )
