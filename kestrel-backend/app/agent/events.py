"""Agent SSE event types — every event the frontend can render."""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThinkingEvent:
    """Agent's reasoning in natural language (no tool names exposed)."""
    content: str = ""
    type: str = "thinking"


@dataclass
class TextEvent:
    """Final response text, streamed token by token."""
    delta: str = ""
    type: str = "text"


@dataclass
class ToolStartEvent:
    """Tool execution started — shown as collapsible in UI."""
    tool_id: str = ""
    display_name: str = ""
    type: str = "tool_start"


@dataclass
class ToolDoneEvent:
    """Tool execution completed.

    Carries everything the UI needs for an expandable Claude-Code-style row:
    `args` — JSON preview of the tool input (only known once execution starts),
    `summary` — short one-line result, `result` — a fuller (capped) result preview.
    """
    tool_id: str = ""
    summary: str = ""
    duration_ms: int = 0
    args: str = ""
    result: str = ""
    type: str = "tool_done"


@dataclass
class RichCardEvent:
    """Structured rich output (stock card, chart, table)."""
    card_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    type: str = "rich_card"


@dataclass
class AskUserEvent:
    """Pause loop and request clarification from user."""
    question: str = ""
    options: list[str] = field(default_factory=list)
    clarification_id: str = ""
    type: str = "ask_user"


@dataclass
class StatusEvent:
    """Agent status change for UI state indicators.

    Optional detail fields carry context for pet events (e.g. a `pet_leveled`
    status includes the new level and any milestone bonus pull granted).
    """
    status: str = ""
    detail: dict[str, Any] | None = None
    type: str = "status"


@dataclass
class FollowUpEvent:
    """Suggested follow-up questions (Perplexity-style chips)."""
    suggestions: list[str] = field(default_factory=list)
    type: str = "follow_up"


@dataclass
class ErrorEvent:
    """Structured error — allows frontend to show retry UI."""
    message: str = ""
    code: str = "stream_error"
    recoverable: bool = True
    type: str = "error"


@dataclass
class DoneEvent:
    """Turn complete — final metadata."""
    cost: float = 0.0
    tokens_used: int = 0
    model: str = ""
    tools_called: list[str] = field(default_factory=list)
    turn_id: str = ""
    # The conversation's session id — the client stores this and sends it back on
    # the next turn so all turns group under one session (not one-per-message).
    session_id: str = ""
    context_usage: dict[str, Any] | None = None
    # Observability trace for this turn (carried per-request, not via shared loop state).
    # Excluded from client serialization by the SSE serializer.
    trace: Any = None
    type: str = "done"


AgentEvent = (
    ThinkingEvent | TextEvent | ToolStartEvent | ToolDoneEvent |
    RichCardEvent | AskUserEvent | StatusEvent | FollowUpEvent | ErrorEvent | DoneEvent
)


def event_to_dict(event: AgentEvent) -> dict[str, Any]:
    """Client-safe dict for an event.

    `trace` is an internal observability object carried on DoneEvent for the
    server to persist — it is never sent to the client.
    """
    return {k: v for k, v in event.__dict__.items() if k != "trace"}


def serialize_event(event: AgentEvent) -> str:
    """Serialize event to SSE data line."""
    return f"data: {json.dumps(event_to_dict(event), ensure_ascii=False)}\n\n"
