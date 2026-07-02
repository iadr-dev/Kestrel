"""Telegram Update parser — extracts messages and callback queries."""

import json

from app.channels.base import IncomingMessage


def parse_telegram_update(body: bytes) -> list[IncomingMessage]:
    """Parse Telegram Update object into IncomingMessage."""
    data = json.loads(body)
    messages: list[IncomingMessage] = []

    if "message" in data:
        msg = data["message"]
        text = msg.get("text", "")
        if text:
            from_user = msg.get("from", {})
            messages.append(IncomingMessage(
                channel="telegram",
                channel_user_id=str(from_user.get("id", "")),
                chat_id=str(msg["chat"]["id"]),
                text=text,
                message_id=str(msg.get("message_id", "")),
                display_name=from_user.get("first_name"),
                raw_event=data,
            ))

    elif "callback_query" in data:
        cb = data["callback_query"]
        cb_data = cb.get("data", "")
        if cb_data:
            from_user = cb.get("from", {})
            chat = cb.get("message", {}).get("chat", {})
            messages.append(IncomingMessage(
                channel="telegram",
                channel_user_id=str(from_user.get("id", "")),
                chat_id=str(chat.get("id", from_user.get("id", ""))),
                text=cb_data,
                message_id=str(cb.get("id", "")),
                display_name=from_user.get("first_name"),
                raw_event=data,
            ))

    return messages
