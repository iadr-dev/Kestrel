"""Telegram message builders — MarkdownV2 formatting, inline keyboards."""

from typing import Any

from app.channels.base import OutgoingMessage


def to_telegram_payload(msg: OutgoingMessage, chat_id: str) -> dict[str, Any]:
    """Convert OutgoingMessage to Telegram sendMessage payload."""
    payload: dict[str, Any] = {"chat_id": chat_id}

    if msg.text:
        payload["text"] = escape_markdown_v2(msg.text[:4096])
        payload["parse_mode"] = "MarkdownV2"

    if msg.buttons:
        keyboard = []
        for btn in msg.buttons[:10]:
            keyboard.append([{
                "text": btn["text"][:64],
                "callback_data": btn["data"][:64],
            }])
        payload["reply_markup"] = {"inline_keyboard": keyboard}

    if msg.rich_card:
        card_text = format_rich_card(msg.rich_card)
        payload["text"] = escape_markdown_v2(card_text)
        payload["parse_mode"] = "MarkdownV2"

    return payload


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    result = ""
    for char in text:
        if char in special_chars:
            result += f"\\{char}"
        else:
            result += char
    return result


def format_rich_card(data: dict[str, Any]) -> str:
    """Format rich card data as readable text for Telegram."""
    parts: list[str] = []
    stock_id = data.get("stock_id", "")
    stock_name = data.get("stock_name", stock_id)

    parts.append(f"📊 {stock_name} ({stock_id})")

    if "score" in data:
        emoji = "🟢" if data["score"] >= 70 else "🟡" if data["score"] >= 50 else "🔴"
        parts.append(f"{emoji} 綜合評分: {data['score']}/100")

    if "conclusion" in data:
        parts.append(f"結論: {data['conclusion']}")

    if "reasoning" in data:
        parts.append(f"\n{data['reasoning'][:300]}")

    return "\n".join(parts)
