"""Agent tools powered by yfinance — comprehensive US/TW stock data via Yahoo Finance."""

from typing import Any

from app.agent.tools.base import ToolResult
from app.providers.yfinance import YFinanceProvider

_yf = YFinanceProvider()


class GetAnalystTargetTool:
    name = "get_analyst_target"
    description = "Get analyst consensus target price and buy/hold/sell recommendations for a stock. Works for both TW and US stocks."
    display_name_template = "查詢{stock_id}分析師目標價"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330' for TSMC, 'NVDA' for NVIDIA)"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        info = await _yf.get_info(stock_id)

        if info.get("error"):
            return ToolResult(content=f"{stock_id}: 無法取得分析師資料", error=info["error"])

        target = info.get("target_mean_price")
        high = info.get("target_high_price")
        low = info.get("target_low_price")
        rec = info.get("recommendation", "")
        pe = info.get("pe_ratio")
        name = info.get("name", stock_id)

        lines = [f"{name} ({stock_id})"]
        if target:
            lines.append(f"分析師目標價: ${target:.1f} (最高 ${high:.1f}, 最低 ${low:.1f})")
        if rec:
            lines.append(f"投資建議: {rec.upper()}")
        if pe:
            lines.append(f"本益比: {pe:.1f}")

        return ToolResult(
            content="\n".join(lines),
            data={"target_mean": target, "target_high": high, "target_low": low, "recommendation": rec, "pe_ratio": pe},
        )


class GetEarningsCalendarTool:
    name = "get_earnings_calendar"
    description = "Get upcoming earnings date, dividend dates, and EPS estimates for a stock."
    display_name_template = "查詢{stock_id}財報日程"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330', 'NVDA')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        cal = await _yf.get_calendar(stock_id)

        if cal.get("error"):
            return ToolResult(content=f"{stock_id}: 無法取得行事曆資料", error=cal["error"])

        lines = [f"{stock_id} 行事曆:"]
        if cal.get("Earnings Date"):
            dates = cal["Earnings Date"] if isinstance(cal["Earnings Date"], list) else [cal["Earnings Date"]]
            lines.append(f"下次法說會/財報: {dates[0]}")
        if cal.get("Earnings Average"):
            lines.append(f"EPS 預估: {cal['Earnings Average']:.2f}")
        if cal.get("Ex-Dividend Date"):
            lines.append(f"除息日: {cal['Ex-Dividend Date']}")
        if cal.get("Dividend Date"):
            lines.append(f"股利發放日: {cal['Dividend Date']}")

        return ToolResult(content="\n".join(lines), data=cal)


class GetHoldersTool:
    name = "get_holders"
    description = "Get top institutional holders and recent insider transactions for a stock."
    display_name_template = "查詢{stock_id}持股人"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330', 'AAPL')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        holders = await _yf.get_holders(stock_id)
        insiders = await _yf.get_insider_transactions(stock_id)

        lines = [f"{stock_id} 持股資訊:"]

        institutional = holders.get("institutional", [])
        if institutional:
            lines.append(f"\n主要機構持股 (前{min(5, len(institutional))}名):")
            for h in institutional[:5]:
                name = h.get("Holder", h.get("holder", ""))
                pct = h.get("% Out", h.get("pct_held", ""))
                lines.append(f"  • {name} — {pct}")

        transactions = insiders.get("transactions", [])
        if transactions:
            lines.append(f"\n近期內部人交易 (前{min(5, len(transactions))}筆):")
            for tx in transactions[:5]:
                insider = tx.get("Insider", tx.get("insider", ""))
                action = tx.get("Transaction", tx.get("transaction", ""))
                shares = tx.get("Shares", tx.get("shares", ""))
                lines.append(f"  • {insider}: {action} {shares}股")

        return ToolResult(
            content="\n".join(lines),
            data={"institutional": institutional[:5], "insider_transactions": transactions[:5]},
        )


class GetStockHistoryTool:
    name = "get_stock_history"
    description = "Get historical OHLCV price data for any stock (TW or US). Supports various periods (1d to max) and intervals (1m to 1mo)."
    display_name_template = "查詢{stock_id}歷史K線"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330', 'AAPL')"},
            "period": {"type": "string", "description": "Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max", "default": "1mo"},
            "interval": {"type": "string", "description": "Interval: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo", "default": "1d"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        period = args.get("period", "1mo")
        interval = args.get("interval", "1d")
        data = await _yf.get_history(stock_id, period, interval)

        if not data:
            return ToolResult(content=f"{stock_id}: 無歷史資料")

        latest = data[-1]
        first = data[0]
        lines = [
            f"{stock_id} 歷史K線 ({period}, {interval}): {len(data)}筆",
            f"最新: O:{latest.get('Open', '?')} H:{latest.get('High', '?')} L:{latest.get('Low', '?')} C:{latest.get('Close', '?')}",
            f"期間起始: {first.get('Date', first.get('Datetime', '?'))}",
        ]
        return ToolResult(content="\n".join(lines), data={"count": len(data), "latest": latest, "first": first})


class GetFinancialsTool:
    name = "get_yf_financials"
    description = "Get annual financial statements (income statement, balance sheet, cash flow) for a stock via Yahoo Finance."
    display_name_template = "查詢{stock_id}財務報表(YF)"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. 'AAPL', '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        data = await _yf.get_financials(stock_id)

        if data.get("error"):
            return ToolResult(content=f"{stock_id}: 無法取得財報", error=data["error"])

        has_income = "income_statement" in data
        has_bs = "balance_sheet" in data
        has_cf = "cash_flow" in data
        lines = [f"{stock_id} 年度財報:"]
        if has_income:
            lines.append(f"  損益表: {len(data['income_statement'].get('columns', []))}期")
        if has_bs:
            lines.append(f"  資產負債表: {len(data['balance_sheet'].get('columns', []))}期")
        if has_cf:
            lines.append(f"  現金流量表: {len(data['cash_flow'].get('columns', []))}期")

        return ToolResult(content="\n".join(lines), data=data)


class GetMarketSearchTool:
    name = "search_stocks"
    description = "Search for stocks/ETFs/crypto by keyword. Returns matching tickers with name, exchange, and type."
    display_name_template = "搜尋{query}"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword (company name, symbol, etc.)"},
            "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
        },
        "required": ["query"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        query = args["query"]
        limit = args.get("limit", 10)
        data = await _yf.search(query, limit)

        if not data:
            return ToolResult(content=f"搜尋 '{query}': 無結果")

        lines = [f"搜尋 '{query}' ({len(data)}筆):", ""]
        for r in data:
            lines.append(f"  {r['symbol']} — {r['name']} ({r.get('exchange', '')}, {r.get('type', '')})")

        return ToolResult(content="\n".join(lines), data={"results": data})


class GetMarketScreenerTool:
    name = "screen_us_stocks"
    description = "Run predefined US stock screener: most_actives, day_gainers, day_losers, growth_technology_stocks, undervalued_large_caps, etc."
    display_name_template = "篩選{screen_name}"
    parameters = {
        "type": "object",
        "properties": {
            "screen_name": {"type": "string", "description": "Screener name: most_actives, day_gainers, day_losers, growth_technology_stocks, undervalued_large_caps"},
            "size": {"type": "integer", "description": "Number of results (default 10)", "default": 10},
        },
        "required": ["screen_name"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        screen_name = args["screen_name"]
        size = args.get("size", 10)
        data = await _yf.screen(screen_name, size)

        if not data:
            return ToolResult(content=f"篩選 '{screen_name}': 無結果")

        lines = [f"篩選 '{screen_name}' ({len(data)}筆):", ""]
        for r in data:
            lines.append(f"  {r['symbol']} {r.get('name', '')}: ${r.get('price', '?')} ({r.get('change_pct', 0):+.2f}%) Vol:{r.get('volume', 0):,}")

        return ToolResult(content="\n".join(lines), data={"results": data})


class GetSectorInfoTool:
    name = "get_sector_info"
    description = "Get sector or industry information with top companies. Shows sector performance and leading stocks."
    display_name_template = "查詢{key}產業資訊"
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Sector or industry key (e.g. 'technology', 'semiconductors', 'healthcare')"},
            "type": {"type": "string", "description": "'sector' or 'industry'", "default": "sector"},
        },
        "required": ["key"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        key = args["key"]
        query_type = args.get("type", "sector")

        if query_type == "industry":
            data = await _yf.get_industry(key)
        else:
            data = await _yf.get_sector(key)

        if data.get("error"):
            return ToolResult(content=f"'{key}': 無法取得產業資料", error=data["error"])

        name = data.get("name", key)
        top = data.get("top_companies", [])
        lines = [f"{name}:"]
        if top:
            lines.append(f"\n前{min(10, len(top))}大公司:")
            for c in top[:10]:
                symbol = c.get("symbol", c.get("index", ""))
                lines.append(f"  • {symbol}")

        return ToolResult(content="\n".join(lines), data=data)


class GetNewsTool:
    name = "get_stock_news"
    description = "Get recent news articles for a specific stock from Yahoo Finance."
    display_name_template = "查詢{stock_id}新聞"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. 'AAPL', '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        data = await _yf.get_news(stock_id)

        if not data:
            return ToolResult(content=f"{stock_id}: 無新聞資料")

        lines = [f"{stock_id} 近期新聞:", ""]
        for n in data[:8]:
            lines.append(f"  • {n.get('title', '')} — {n.get('publisher', '')}")

        return ToolResult(content="\n".join(lines), data={"news": data[:10]})


class GetPeersTool:
    name = "get_peers"
    description = "Get peer companies in the same industry for comparison. Shows which stocks compete in the same space."
    display_name_template = "查詢{stock_id}同業比較"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. 'AAPL', '2330')"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        data = await _yf.get_peers(stock_id)

        peers = data.get("peers", [])
        industry = data.get("industry", "")
        sector = data.get("sector", "")

        lines = [f"{stock_id} 同業:"]
        if industry:
            lines.append(f"產業: {industry} | 部門: {sector}")
        if peers:
            lines.append(f"同業公司: {', '.join(peers[:10])}")
        else:
            lines.append("無同業資料")

        return ToolResult(content="\n".join(lines), data=data)
