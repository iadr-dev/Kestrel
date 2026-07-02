"""Message formatter — converts AgentEvent stream to channel OutgoingMessages."""

from app.agent.events import (
    AgentEvent,
    AskUserEvent,
    FollowUpEvent,
    RichCardEvent,
    TextEvent,
)
from app.channels.base import OutgoingMessage


class MessageFormatter:
    """Converts a collected list of AgentEvents into channel-friendly messages."""

    def format_events(self, events: list[AgentEvent], channel: str) -> list[OutgoingMessage]:
        text_parts: list[str] = []
        messages: list[OutgoingMessage] = []

        for event in events:
            match event:
                case TextEvent(delta=d):
                    text_parts.append(d)
                case FollowUpEvent(suggestions=suggestions):
                    if suggestions:
                        messages.append(OutgoingMessage(
                            text="你可能還想了解：",
                            buttons=[{"text": q, "data": q} for q in suggestions],
                        ))
                case RichCardEvent(card_type=card_type, data=data):
                    messages.append(OutgoingMessage(rich_card={"type": card_type, **data}))
                case AskUserEvent(question=question, options=options):
                    messages.append(OutgoingMessage(
                        text=question,
                        buttons=[{"text": o, "data": o} for o in options] if options else None,
                    ))
                case _:
                    pass

        if text_parts:
            full_text = "".join(text_parts)
            # Channel message limits: LINE 5000 chars, Telegram 4096 chars
            max_len = 4096 if channel == "telegram" else 5000
            if len(full_text) > max_len:
                full_text = full_text[:max_len - 20] + "\n\n...（內容過長已截斷）"
            messages.insert(0, OutgoingMessage(text=full_text))

        return messages if messages else [OutgoingMessage(text="（無回應）")]
