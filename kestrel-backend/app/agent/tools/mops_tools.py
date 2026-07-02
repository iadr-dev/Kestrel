"""Agent tools powered by MOPS — announcements, treasury stock, investor conferences, director holdings."""

from typing import Any

from app.agent.tools.base import ToolResult
from app.providers.mops import get_mops_client


class GetAnnouncementsTool:
    name = "get_announcements"
    description = "Search MOPS material announcements (重大訊息) for Taiwan stocks. Can filter by stock code or keyword. Returns recent corporate disclosures."
    display_name_template = "查詢重大訊息"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock code to filter (optional, e.g. '2330')"},
            "keyword": {"type": "string", "description": "Keyword to search (optional, e.g. '董事長', '減資', '合併')"},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_mops_client()
        data = await client.get_announcements(
            stock_id=args.get("stock_id"),
            keyword=args.get("keyword"),
        )

        if not data:
            return ToolResult(content="查無重大訊息", data={"announcements": []})

        lines = [f"重大訊息 ({len(data)}筆):", ""]
        for a in data[:10]:
            lines.append(f"  {a.get('date', '')} {a.get('stock_id', '')} {a.get('company_name', '')}")
            lines.append(f"    {a.get('subject', '')}")

        return ToolResult(content="\n".join(lines), data={"announcements": data[:20]})


class GetTreasuryStockTool:
    name = "get_treasury_stock"
    description = "Get treasury stock buyback records (庫藏股) for a TW stock. Shows buyback purpose, planned/executed shares, and period. Bullish signal when companies buy back their own stock."
    display_name_template = "查詢{stock_id}庫藏股"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_mops_client()
        data = await client.get_treasury_stock(args["stock_id"])

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無庫藏股紀錄", data={"records": []})

        lines = [f"{args['stock_id']} 庫藏股 ({len(data)}筆):", ""]
        for r in data[:5]:
            lines.append(f"  第{r.get('sequence', '?')}次: {r.get('purpose', '')}")
            lines.append(f"    期間: {r.get('period_start', '')}~{r.get('period_end', '')} | 預定:{r.get('planned_shares', '')}股")

        return ToolResult(content="\n".join(lines), data={"records": data})


class GetInvestorConferenceTool:
    name = "get_investor_conferences"
    description = "Get investor conference (法說會) schedule from MOPS. Shows upcoming corporate presentations. Key events that often move stock prices."
    display_name_template = "查詢法說會"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock code to filter (optional)"},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_mops_client()
        data = await client.get_investor_conferences(stock_id=args.get("stock_id"))

        if not data:
            return ToolResult(content="查無法說會資訊", data={"conferences": []})

        lines = [f"法說會 ({len(data)}筆):", ""]
        for c in data[:10]:
            lines.append(f"  {c.get('date', '')} {c.get('company_name', '')} — {c.get('topic', '')}")

        return ToolResult(content="\n".join(lines), data={"conferences": data[:20]})


class GetDirectorHoldingsTool:
    name = "get_director_holdings"
    description = "Get director/supervisor shareholding changes (董監持股異動) from MOPS. Shows insider buying/selling activity — key signal for institutional confidence."
    display_name_template = "查詢{stock_id}董監持股"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Taiwan stock code (e.g. '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_mops_client()
        data = await client.get_director_holdings(args["stock_id"])

        if not data:
            return ToolResult(content=f"{args['stock_id']}: 無董監持股異動資料", data={"records": []})

        lines = [f"{args['stock_id']} 董監持股 ({len(data)}筆):", ""]
        for r in data[:10]:
            lines.append(f"  {r.get('name', '')} ({r.get('title', '')}): 持股 {r.get('current_shares', '')} | 異動 {r.get('change', '')}")

        return ToolResult(content="\n".join(lines), data={"records": data})
