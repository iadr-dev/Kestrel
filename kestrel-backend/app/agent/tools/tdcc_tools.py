"""Agent tools powered by TDCC OpenAPI — shareholding distribution, director custody, weekly balance."""

from typing import Any

from app.agent.tools.base import ToolResult
from app.providers.tdcc import get_tdcc_client


class GetShareholdingDistributionTool:
    name = "get_shareholding_distribution"
    description = "Get TDCC shareholding distribution by tier for a TW stock. Shows holder count and shares at each level (1-999, 1000-5000, etc.). Key signal for retail vs institutional ownership."
    display_name_template = "查詢{stock_id}股權分散表"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_tdcc_client()
        data = await client.get_shareholding(args["stock_id"])

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無集保股權分散資料", data={"tiers": []})

        lines = [f"{args['stock_id']} 集保股權分散 ({data[0].get('date', '')}):", ""]
        for row in data:
            lines.append(f"  級距{row['level']}: {row['holders']:,}人 | {row['shares']:,}股 | {row['percentage']:.2f}%")

        return ToolResult(content="\n".join(lines), data={"tiers": data})


class GetDirectorCustodyTool:
    name = "get_director_custody"
    description = "Get TDCC director/supervisor segregated custody data for a TW stock. Shows mandatory custody shares and changes."
    display_name_template = "查詢{stock_id}董監分戶保管"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_tdcc_client()
        data = await client.get_director_shareholding(args["stock_id"])

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無董監分戶保管資料", data={"records": []})

        return ToolResult(
            content=f"{args['stock_id']} 董監分戶保管: {len(data)}筆資料",
            data={"records": data},
        )


class GetWeeklyBalanceTool:
    name = "get_weekly_balance"
    description = "Get TDCC weekly custody balance and changes for a TW stock. Shows custody movement trends."
    display_name_template = "查詢{stock_id}週餘額"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
            "market": {"type": "string", "description": "Market: 'listed' or 'otc'", "default": "listed"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_tdcc_client()
        market = args.get("market", "listed")
        data = await client.get_weekly_balance(args["stock_id"], market)

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無週餘額資料", data={"records": []})

        return ToolResult(
            content=f"{args['stock_id']} 集保週餘額: {len(data)}筆",
            data={"records": data},
        )


class GetMonthlyCustodyChangeTool:
    name = "get_monthly_custody_change"
    description = "Get TDCC monthly custody change analysis for a TW stock. Shows month-end balance, change from previous month, and holder count."
    display_name_template = "查詢{stock_id}月異動"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
            "market": {"type": "string", "description": "Market: 'listed', 'otc', or 'emerging'", "default": "listed"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_tdcc_client()
        market = args.get("market", "listed")
        data = await client.get_monthly_changes(args["stock_id"], market)

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無月異動資料", data={"records": []})

        return ToolResult(
            content=f"{args['stock_id']} 集保月異動: {len(data)}筆",
            data={"records": data},
        )
