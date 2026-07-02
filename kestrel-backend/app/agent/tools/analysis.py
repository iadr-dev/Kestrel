"""Analysis tools — technical indicators + composite scoring."""

from datetime import date, timedelta
from typing import Any

from app.agent.tools.base import ToolResult
from app.formulas import compute_indicators
from app.services.data.stock_service import StockService


class GetIndicatorsTool:
    name = "get_indicators"
    description = "Compute technical indicators (MA, KD, MACD, RSI, Bollinger) for a stock's price history."
    display_name_template = "計算 {stock_id} 技術指標"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "indicators": {
                "type": "array",
                "items": {"type": "string", "enum": ["sma", "ema", "ma", "kd", "rsi", "macd", "bollinger", "atr", "obv"]},
                "description": "Which indicators to compute",
            },
            "days": {"type": "integer", "default": 120},
        },
        "required": ["stock_id", "indicators"],
    }

    def __init__(self, stock_service: StockService) -> None:
        self._service = stock_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        indicators = args.get("indicators", ["ma", "kd", "macd"])
        days = args.get("days", 120)
        start_date = date.today() - timedelta(days=days)

        data = await self._service.get_price(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無價格資料，無法計算指標")

        close = [r.get("close", r.get("Close", 0)) for r in data]
        high = [r.get("max", r.get("high", r.get("close", 0))) for r in data]
        low = [r.get("min", r.get("low", r.get("close", 0))) for r in data]
        volume = [r.get("Trading_Volume", r.get("volume", 0)) for r in data]

        specs = [{"name": i, "params": {}} for i in indicators]
        results = compute_indicators(close=close, high=high, low=low, volume=volume, indicators=specs)

        # Summarize latest values
        summary_parts = [f"{stock_id} 技術指標 (最新):"]
        for values in results.values():
            for key, arr in values.items():
                latest = next((v for v in reversed(arr) if v is not None), None)
                if latest is not None:
                    summary_parts.append(f"  {key}: {latest:.2f}")

        return ToolResult(
            content="\n".join(summary_parts),
            data={"indicators": results, "data_points": len(close)},
        )


class GetScoreTool:
    name = "get_score"
    description = "Get composite analysis score (0-100) combining technical, chip, and fundamental factors."
    display_name_template = "計算 {stock_id} 綜合評分"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
        },
        "required": ["stock_id"],
    }

    def __init__(self, stock_service: StockService) -> None:
        self._service = stock_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        start_date = date.today() - timedelta(days=60)

        data = await self._service.get_price(stock_id, start_date)
        if not data or len(data) < 20:
            return ToolResult(content=f"{stock_id}: 資料不足，無法評分")

        close = [r.get("close", r.get("Close", 0)) for r in data]

        # Simple scoring: trend + momentum + volume
        ma5 = sum(close[-5:]) / 5
        ma20 = sum(close[-20:]) / 20
        latest = close[-1]

        trend_score = 40 if latest > ma20 else 20  # Above MA20
        momentum_score = 30 if latest > ma5 else 15  # Above MA5
        direction_score = 30 if close[-1] > close[-5] else 10  # 5-day up

        total = trend_score + momentum_score + direction_score
        label = "偏多" if total >= 70 else ("中性" if total >= 50 else "偏空")

        return ToolResult(
            content=f"{stock_id} 綜合評分: {total}/100 ({label}) — 趨勢{trend_score} 動能{momentum_score} 方向{direction_score}",
            data={"score": total, "label": label, "breakdown": {"trend": trend_score, "momentum": momentum_score, "direction": direction_score}},
        )
