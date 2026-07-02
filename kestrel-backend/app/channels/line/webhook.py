"""LINE webhook event parser — extracts text messages from LINE events array."""

import json

from app.channels.base import IncomingMessage


def parse_line_events(body: bytes) -> list[IncomingMessage]:
    """Parse LINE webhook payload into IncomingMessage objects."""
    data = json.loads(body)
    messages: list[IncomingMessage] = []

    for event in data.get("events", []):
        if event.get("type") == "message":
            msg = event.get("message", {})
            source = event.get("source", {})

            if msg.get("type") == "text":
                messages.append(IncomingMessage(
                    channel="line",
                    channel_user_id=source.get("userId", ""),
                    chat_id=source.get("groupId") or source.get("roomId") or source.get("userId", ""),
                    text=msg.get("text", ""),
                    message_id=msg.get("id", ""),
                    reply_token=event.get("replyToken"),
                    raw_event=event,
                ))
        elif event.get("type") == "postback":
            source = event.get("source", {})
            postback_data = event.get("postback", {}).get("data", "")
            if postback_data:
                messages.append(IncomingMessage(
                    channel="line",
                    channel_user_id=source.get("userId", ""),
                    chat_id=source.get("groupId") or source.get("userId", ""),
                    text=postback_data,
                    message_id=event.get("webhookEventId", ""),
                    reply_token=event.get("replyToken"),
                    raw_event=event,
                ))

    return messages
