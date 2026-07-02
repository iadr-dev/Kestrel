"""Institutional/chip data tools — margin, shareholding, main force, government bank."""

from datetime import date, timedelta
from typing import Any

from app.agent.tools.base import ToolResult
from app.services.data.institutional_service import InstitutionalService


class GetMarginTool:
    name = "get_margin_data"
    description = "Get margin trading data (融資融券) for a stock — shows leverage sentiment."
    display_name_template = "查詢 {stock_id} 融資融券"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330')"},
            "days": {"type": "integer", "description": "Days of history (default 20)", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_margin(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無融資融券資料")
        return ToolResult(
            content=f"{stock_id} 融資融券: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )


class GetShareholdingTool:
    name = "get_shareholding"
    description = "Get shareholding distribution (持股分級) — shows concentration of large holders (千張大戶)."
    display_name_template = "查詢 {stock_id} 持股分級"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "days": {"type": "integer", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_holding_shares_per(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無持股分級資料")
        return ToolResult(
            content=f"{stock_id} 持股分級: {len(data)} 筆",
            data={"records": data[-20:]},
        )


class GetMainForceTool:
    name = "get_main_force"
    description = "Get broker trading daily report (分點主力) — shows which brokers are buying/selling. Sponsor tier only."
    display_name_template = "查詢 {stock_id} 主力分點"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "report_date": {"type": "string", "description": "Date YYYY-MM-DD (default: latest trading day)"},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        report_date_str = args.get("report_date")
        report_date = date.fromisoformat(report_date_str) if report_date_str else date.today()
        data = await self._service.get_trading_daily_report(stock_id=stock_id, report_date=report_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無分點主力資料 (需 Sponsor 會員)")
        return ToolResult(
            content=f"{stock_id} 主力分點 {report_date}: {len(data)} 筆券商",
            data={"records": data[:20]},
        )


class GetGovernmentBankTool:
    name = "get_government_bank"
    description = "Get government bank (八大行庫) buy/sell data — shows national fund activity."
    display_name_template = "查詢八大行庫買賣"
    parameters = {
        "type": "object",
        "properties": {
            "trade_date": {"type": "string", "description": "Date YYYY-MM-DD"},
        },
        "required": [],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        trade_date_str = args.get("trade_date")
        trade_date = date.fromisoformat(trade_date_str) if trade_date_str else date.today()
        data = await self._service.get_government_bank(trade_date)
        if not data:
            return ToolResult(content="無八大行庫資料")
        return ToolResult(
            content=f"八大行庫 {trade_date}: {len(data)} 筆",
            data={"records": data[:20]},
        )


class GetShortSaleBalanceTool:
    name = "get_short_sale_balance"
    description = "Get securities short-sale balance (借券賣出餘額) for a stock — rising balance signals bearish institutional positioning."
    display_name_template = "查詢 {stock_id} 借券賣出餘額"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330')"},
            "days": {"type": "integer", "description": "Days of history (default 20)", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_short_sale_balances(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無借券賣出資料")
        return ToolResult(
            content=f"{stock_id} 借券賣出餘額: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )


class GetSecuritiesLendingTool:
    name = "get_securities_lending"
    description = "Get securities lending (借券) activity for a stock — institutional borrowing that often precedes short selling."
    display_name_template = "查詢 {stock_id} 借券"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "days": {"type": "integer", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_securities_lending(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無借券資料")
        return ToolResult(
            content=f"{stock_id} 借券: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )


class GetBlockTradeTool:
    name = "get_block_trade"
    description = "Get block-trade (鉅額交易) records — large off-market deals that often signal institutional accumulation or distribution."
    display_name_template = "查詢 {stock_id} 鉅額交易"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (optional — omit for market-wide)"},
            "days": {"type": "integer", "default": 20},
        },
        "required": [],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args.get("stock_id")
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_block_trade(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id or '市場'}: 無鉅額交易資料")
        return ToolResult(
            content=f"{stock_id or '市場'} 鉅額交易: {len(data)} 筆 ({days}日)",
            data={"records": data[-15:]},
        )


class GetMarginMaintenanceTool:
    name = "get_margin_maintenance"
    description = "Get market-wide margin maintenance ratio (融資維持率) — a falling ratio warns of margin-call / forced-liquidation risk."
    display_name_template = "查詢融資維持率"
    parameters = {
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Days of history (default 20)", "default": 20},
        },
        "required": [],
    }

    def __init__(self, service: InstitutionalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_margin_maintenance(start_date)
        if not data:
            return ToolResult(content="無融資維持率資料")
        return ToolResult(
            content=f"融資維持率: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )
