"""Ranking / calendar tools backed by official TWSE sources.

Replaces the former HiStock-scraped tools (HiStock is Cloudflare-blocked). Uses
TWSEClient.fetch_report_rows for envelope unwrapping + last-trading-day fallback.
"""

from typing import Any

from app.agent.tools.base import ToolResult
from app.providers.twse import get_twse_client


class GetStockRankingsTool:
    name = "get_stock_rankings"
    description = "Get Taiwan stock market rankings — top stocks by trading volume/turnover. Real-time market leaders."
    display_name_template = "查詢成交量排行"
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stocks (default 20)", "default": 20},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        # MI_INDEX20 = top-20 by volume (排名/證券代號/證券名稱/成交股數/...).
        data = await get_twse_client().fetch_report_rows("MI_INDEX20")
        if not data:
            return ToolResult(content="無法取得成交量排行資料", data={"rankings": []})
        limit = args.get("limit", 20)
        lines = [f"成交量排行 (前{min(limit, len(data))}名):", ""]
        for r in data[:limit]:
            code = r.get("證券代號", r.get("Code", ""))
            name = r.get("證券名稱", r.get("Name", ""))
            vol = r.get("成交股數", r.get("TradeVolume", ""))
            close = r.get("收盤價", r.get("ClosingPrice", ""))
            lines.append(f"  {code} {name}: 收 {close} | 量 {vol}")
        return ToolResult(content="\n".join(lines), data={"rankings": data[:limit]})


class GetInstitutionalRankingsTool:
    name = "get_institutional_rankings"
    description = "Get top stocks by institutional net buy/sell (三大法人買賣超排行) — shows which stocks foreign investors, trusts, and dealers are accumulating or dumping today."
    display_name_template = "查詢法人買賣超排行"
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of stocks (default 20)", "default": 20},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        limit = args.get("limit", 20)
        # T86 = per-stock institutional buy/sell, sorted by |三大法人買賣超| desc.
        data = await get_twse_client().get_institutional_summary(limit=limit)
        if not data:
            return ToolResult(content="無法人買賣超排行資料（可能非交易日）", data={"rankings": []})
        lines = [f"三大法人買賣超排行 (前{min(limit, len(data))}名):", ""]
        for r in data[:limit]:
            code = r.get("證券代號", "")
            name = r.get("證券名稱", "")
            net = r.get("三大法人買賣超股數", "")
            lines.append(f"  {code} {name}: 三大法人淨 {net}")
        return ToolResult(content="\n".join(lines), data={"rankings": data[:limit]})


class GetMarginRankingsTool:
    name = "get_margin_rankings"
    description = "Get market-wide margin trading (融資融券) totals — financing/short-selling balances and daily changes, a gauge of retail leverage sentiment."
    display_name_template = "查詢融資融券"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        # MI_MARGN selectType=ALL = market-wide margin/short summary.
        data = await get_twse_client().fetch_report_rows("MI_MARGN", extra_params={"selectType": "ALL"})
        if not data:
            return ToolResult(content="無融資融券資料（可能非交易日）", data={"rankings": []})
        lines = ["融資融券市場概況:", ""]
        for r in data[:15]:
            item = r.get("項目", "")
            buy = r.get("買進", "")
            sell = r.get("賣出", "")
            bal = r.get("今日餘額", r.get("前日餘額", ""))
            lines.append(f"  {item}: 買 {buy} 賣 {sell} 餘額 {bal}")
        return ToolResult(content="\n".join(lines), data={"rankings": data})
