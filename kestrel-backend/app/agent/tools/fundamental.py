"""Fundamental data tools — financials, dividends, market value."""

from datetime import date, timedelta
from typing import Any

from app.agent.tools.base import ToolResult
from app.services.data.fundamental_service import FundamentalService


class GetFinancialsTool:
    name = "get_financials"
    description = "Get financial statements (income statement, balance sheet, cash flow) for a stock."
    display_name_template = "查詢 {stock_id} 財報"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "statement_type": {
                "type": "string",
                "enum": ["income", "balance", "cashflow", "all"],
                "description": "Which statement (default: income)",
                "default": "income",
            },
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: FundamentalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        stmt_type = args.get("statement_type", "income")
        start_date = date.today() - timedelta(days=730)

        match stmt_type:
            case "income" | "all":
                data = await self._service.get_income_statement(stock_id, start_date)
            case "balance":
                data = await self._service.get_balance_sheet(stock_id, start_date)
            case "cashflow":
                data = await self._service.get_cash_flow(stock_id, start_date)
            case _:
                data = await self._service.get_income_statement(stock_id, start_date)

        if not data:
            return ToolResult(content=f"{stock_id}: 無財報資料")
        return ToolResult(
            content=f"{stock_id} 財報 ({stmt_type}): {len(data)} 筆",
            data={"records": data[-30:]},
        )


class GetDividendTool:
    name = "get_dividend"
    description = "Get dividend policy and ex-dividend results (股利政策 + 除權息) for a stock."
    display_name_template = "查詢 {stock_id} 股利"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "years": {"type": "integer", "description": "Years of history (default 5)", "default": 5},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: FundamentalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        years = args.get("years", 5)
        start_date = date.today() - timedelta(days=years * 365)
        data = await self._service.get_dividend(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無股利資料")
        return ToolResult(
            content=f"{stock_id} 股利政策: {len(data)} 年",
            data={"records": data},
        )


class GetMarketValueTool:
    name = "get_market_value"
    description = "Get stock market capitalization (市值) and market value weight (市值比重)."
    display_name_template = "查詢 {stock_id} 市值"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: FundamentalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        start_date = date.today() - timedelta(days=90)
        data = await self._service.get_market_value(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無市值資料")
        latest = data[-1]
        mv = latest.get("market_value", 0)
        return ToolResult(
            content=f"{stock_id} 市值: {mv:,.0f}",
            data={"records": data[-5:]},
        )


class GetCapitalReductionTool:
    name = "get_capital_reduction"
    description = "Get capital-reduction (減資) history for a stock — share-count reductions that affect EPS and price reference."
    display_name_template = "查詢 {stock_id} 減資"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330')"},
            "years": {"type": "integer", "description": "Years of history (default 3)", "default": 3},
        },
        "required": ["stock_id"],
    }

    def __init__(self, service: FundamentalService) -> None:
        self._service = service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        years = args.get("years", 3)
        start_date = date.today() - timedelta(days=365 * years)
        data = await self._service.get_capital_reduction(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無減資紀錄")
        return ToolResult(
            content=f"{stock_id} 減資紀錄: {len(data)} 筆 ({years}年)",
            data={"records": data},
        )
