"""User interaction tools — schedule alerts, set preferences."""

from typing import Any

from app.agent.tools.base import ToolResult


class ScheduleAlertTool:
    name = "schedule_alert"
    description = "Set up a price alert for the user. Will notify when condition is met."
    display_name_template = "設定 {stock_id} 到價提醒"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID to monitor"},
            "condition": {
                "type": "string",
                "enum": ["above", "below", "change_pct"],
                "description": "Trigger when price goes above/below threshold, or changes by pct",
            },
            "threshold": {"type": "number", "description": "Price threshold or percentage"},
            "message": {"type": "string", "description": "Custom message for the alert"},
        },
        "required": ["stock_id", "condition", "threshold"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        condition = args["condition"]
        threshold = args["threshold"]
        message = args.get("message", "")

        condition_text = {"above": "突破", "below": "跌破", "change_pct": "波動超過"}
        desc = f"{stock_id} {condition_text.get(condition, condition)} {threshold}"

        return ToolResult(
            content=f"已設定提醒: {desc}" + (f" ({message})" if message else ""),
            data={
                "type": "alert_created",
                "stock_id": stock_id,
                "condition": condition,
                "threshold": threshold,
                "message": message,
            },
        )


class SetPreferenceTool:
    name = "set_preference"
    description = "Update a user preference (language, analysis style, default market, risk level)."
    display_name_template = "更新使用者偏好"
    parameters = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "enum": ["language", "analysis_style", "default_market", "risk_level", "notification_channel"],
                "description": "Which preference to set",
            },
            "value": {"type": "string", "description": "New value for the preference"},
        },
        "required": ["key", "value"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        key = args["key"]
        value = args["value"]
        return ToolResult(
            content=f"偏好已更新: {key} = {value}",
            data={"updated": True, "key": key, "value": value},
        )
