"""LINE rich message builders — Flex Messages, Quick Reply, Templates."""

from typing import Any

from app.channels.base import OutgoingMessage


def to_line_message(msg: OutgoingMessage) -> dict[str, Any]:
    """Convert OutgoingMessage to LINE message format."""
    if msg.rich_card:
        return build_flex_card(msg.rich_card)
    if msg.buttons and msg.text:
        return build_quick_reply_text(msg.text, msg.buttons)
    if msg.buttons:
        return build_quick_reply_text("請選擇：", msg.buttons)
    if msg.text:
        return {"type": "text", "text": msg.text[:5000]}
    return {"type": "text", "text": "（無內容）"}


def build_quick_reply_text(text: str, buttons: list[dict[str, str]]) -> dict[str, Any]:
    """Text message with quick reply buttons at bottom."""
    items = []
    for btn in buttons[:13]:  # LINE max 13 quick reply items
        items.append({
            "type": "action",
            "action": {
                "type": "message",
                "label": btn["text"][:20],
                "text": btn["data"][:300],
            },
        })
    return {
        "type": "text",
        "text": text[:5000],
        "quickReply": {"items": items},
    }


def build_flex_card(data: dict[str, Any]) -> dict[str, Any]:
    """Build a Flex Message bubble for stock analysis cards."""
    stock_id = data.get("stock_id", "")
    stock_name = data.get("stock_name", stock_id)

    body_contents: list[dict[str, Any]] = [
        {"type": "text", "text": f"{stock_name} ({stock_id})", "weight": "bold", "size": "lg"},
    ]

    if "score" in data:
        body_contents.append({
            "type": "text",
            "text": f"綜合評分: {data['score']}/100",
            "size": "md",
            "color": "#27AE60" if data["score"] >= 70 else "#F39C12" if data["score"] >= 50 else "#E74C3C",
        })

    if "conclusion" in data:
        body_contents.append({
            "type": "text", "text": f"結論: {data['conclusion']}", "size": "sm", "wrap": True,
        })

    if "reasoning" in data:
        body_contents.append({
            "type": "text", "text": data["reasoning"][:200], "size": "xs", "color": "#888888", "wrap": True,
        })

    return {
        "type": "flex",
        "altText": f"{stock_name} 分析",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents,
                "spacing": "sm",
                "paddingAll": "15px",
            },
        },
    }
