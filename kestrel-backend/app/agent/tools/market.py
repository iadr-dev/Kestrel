"""Market data tools — wraps existing StockService, MarketService, ScreenerService."""

from datetime import date, timedelta
from typing import Any

from app.agent.tools.base import ToolResult
from app.services.data.derivative_service import DerivativeService
from app.services.data.fundamental_service import FundamentalService
from app.services.data.institutional_service import InstitutionalService
from app.services.data.international_service import InternationalService
from app.services.data.macro_service import MacroService
from app.services.data.market_service import MarketService
from app.services.data.screener_service import ScreenerService
from app.services.data.stock_service import StockService


class GetStockPriceTool:
    name = "get_stock_price"
    description = "Get stock OHLCV price data with optional technical indicators. Use for any stock price query."
    display_name_template = "查詢 {stock_id} 股價資料"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330' for TSMC, 'AAPL' for Apple)"},
            "days": {"type": "integer", "description": "Number of days of history (default 60)", "default": 60},
            "indicators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Technical indicators to compute: sma, ema, macd, kd, rsi, bollinger",
            },
        },
        "required": ["stock_id"],
    }

    def __init__(self, stock_service: StockService) -> None:
        self._service = stock_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 60)
        indicators = args.get("indicators")

        start_date = date.today() - timedelta(days=days)
        end_date = date.today()

        if indicators:
            indicator_specs = [{"name": i, "params": {}} for i in indicators]
            result = await self._service.get_price_with_indicators(
                stock_id, start_date, end_date, indicator_specs
            )
            data = result.get("data", [])
            ind = result.get("indicators", {})
            summary = f"{stock_id}: {len(data)} 日資料, 指標: {', '.join(ind.keys())}"
            if data:
                latest = data[-1]
                close = latest.get("close", latest.get("Close"))
                summary += f", 最新收盤: {close}"
            return ToolResult(content=summary, data=result)
        else:
            data = await self._service.get_price(stock_id, start_date, end_date)
            if not data:
                return ToolResult(content=f"{stock_id}: 無資料", error="No data found")
            latest = data[-1]
            close = latest.get("close", latest.get("Close"))
            volume = latest.get("Trading_Volume", latest.get("volume", 0))
            return ToolResult(
                content=f"{stock_id}: {len(data)} 日, 最新收盤 {close}, 成交量 {volume:,}",
                data={"records": data[-10:], "total_count": len(data)},
            )


class GetDayTradingTool:
    name = "get_day_trading"
    description = "Get day-trading activity (當日沖銷) for a stock — day-trade volume/ratio, a gauge of short-term speculation."
    display_name_template = "查詢 {stock_id} 當沖"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330')"},
            "days": {"type": "integer", "description": "Days of history (default 20)", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, stock_service: StockService) -> None:
        self._service = stock_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_day_trading(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無當沖資料")
        return ToolResult(
            content=f"{stock_id} 當沖: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )


class GetMarketIndexTool:
    name = "get_market_index"
    description = "Get TAIEX (加權指數) intraday data for a specific trading date."
    display_name_template = "查詢加權指數"
    parameters = {
        "type": "object",
        "properties": {
            "trade_date": {"type": "string", "description": "Trading date YYYY-MM-DD (default: today)"},
        },
        "required": [],
    }

    def __init__(self, market_service: MarketService) -> None:
        self._service = market_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        trade_date_str = args.get("trade_date")
        trade_date = date.fromisoformat(trade_date_str) if trade_date_str else date.today()
        data = await self._service.get_taiex(trade_date)
        if not data:
            return ToolResult(content="無加權指數資料", data={"records": []})
        return ToolResult(
            content=f"加權指數 {trade_date}: {len(data)} 筆資料",
            data={"records": data[-5:]},
        )


class GetAdvanceDeclineTool:
    name = "get_advance_decline"
    description = "Get market breadth (漲跌家數) for a trading day — counts of advancing vs declining stocks. A core market-sentiment gauge."
    display_name_template = "查詢漲跌家數"
    parameters = {
        "type": "object",
        "properties": {
            "trade_date": {"type": "string", "description": "Trading date YYYY-MM-DD (default: latest)"},
        },
        "required": [],
    }

    def __init__(self, market_service: MarketService) -> None:
        self._service = market_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        from app.db.duckdb.engine import get_duckdb

        trade_date_str = args.get("trade_date")
        target = date.fromisoformat(trade_date_str) if trade_date_str else date.today()

        # Pull the latest available day on/before target from DuckDB (pre-ingested).
        rows: list[tuple[Any, ...]] = []
        used_date = target
        db = get_duckdb()
        for offset in range(6):
            d = target - timedelta(days=offset)
            rows = await db.aquery(
                "SELECT close, spread FROM price_daily WHERE date = ? AND close > 0",
                [str(d)],
            )
            if rows:
                used_date = d
                break
        if not rows:
            return ToolResult(content=f"{target}: 無漲跌家數資料（DuckDB 無當日價格）")

        up = down = flat = 0
        for _close, spread in rows:
            if spread is None:
                continue
            if spread > 0:
                up += 1
            elif spread < 0:
                down += 1
            else:
                flat += 1
        total = up + down + flat
        return ToolResult(
            content=f"漲跌家數 {used_date}: 上漲 {up} / 下跌 {down} / 平盤 {flat}（共 {total} 檔）",
            data={"date": str(used_date), "up": up, "down": down, "flat": flat, "total": total},
        )


class GetForeignByIndustryTool:
    name = "get_foreign_by_industry"
    description = "Get foreign-investor net buy/sell by industry (外資產業別買賣超) — shows which sectors foreign capital is rotating into/out of."
    display_name_template = "查詢外資產業別買賣超"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        from app.providers.twse import get_twse_client

        # fetch_report_rows unwraps the {stat,fields,data} envelope and walks back
        # to the last trading day with data.
        data = await get_twse_client().fetch_report_rows("MI_QFIIS_cat", fund=True)
        if not data:
            return ToolResult(content="無外資產業別買賣超資料", data=[])
        return ToolResult(
            content=f"外資產業別買賣超: {len(data)} 個產業",
            data={"records": data},
        )


class GetInstitutionalFlowTool:
    name = "get_institutional_flow"
    description = "Get institutional investor buy/sell data (三大法人買賣超) for a stock."
    display_name_template = "查詢 {stock_id} 法人買賣"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID (e.g. '2330')"},
            "days": {"type": "integer", "description": "Days of history (default 20)", "default": 20},
        },
        "required": ["stock_id"],
    }

    def __init__(self, institutional_service: InstitutionalService) -> None:
        self._service = institutional_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        days = args.get("days", 20)
        start_date = date.today() - timedelta(days=days)
        data = await self._service.get_buy_sell(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無法人資料")
        return ToolResult(
            content=f"{stock_id} 法人買賣: {len(data)} 筆 ({days}日)",
            data={"records": data[-10:]},
        )


class GetRevenueTool:
    name = "get_revenue"
    description = "Get monthly revenue data (月營收) for a stock. Shows revenue trend."
    display_name_template = "查詢 {stock_id} 營收"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ID"},
            "months": {"type": "integer", "description": "Months of history (default 12)", "default": 12},
        },
        "required": ["stock_id"],
    }

    def __init__(self, fundamental_service: FundamentalService) -> None:
        self._service = fundamental_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        months = args.get("months", 12)
        start_date = date.today() - timedelta(days=months * 31)
        data = await self._service.get_revenue(stock_id, start_date)
        if not data:
            return ToolResult(content=f"{stock_id}: 無營收資料")
        latest = data[-1] if data else {}
        revenue = latest.get("revenue", 0)
        return ToolResult(
            content=f"{stock_id} 營收: 最新 {revenue:,.0f}, 共 {len(data)} 個月",
            data={"records": data},
        )


class GetMacroDataTool:
    name = "get_macro_data"
    description = "Get macro economic data: exchange rates, interest rates, gold, oil, bonds, or Fear & Greed index."
    display_name_template = "查詢總經數據 ({data_type})"
    parameters = {
        "type": "object",
        "properties": {
            "data_type": {
                "type": "string",
                "enum": ["exchange_rate", "interest_rate", "gold", "oil", "bonds", "fear_greed", "business_indicator"],
                "description": "Type of macro data",
            },
            "identifier": {"type": "string", "description": "e.g. 'USD', 'FED', 'WTI', 'United States 10-Year'"},
            "days": {"type": "integer", "default": 30},
        },
        "required": ["data_type"],
    }

    def __init__(self, macro_service: MacroService) -> None:
        self._service = macro_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data_type = args["data_type"]
        identifier = args.get("identifier", "")
        days = args.get("days", 30)
        start_date = date.today() - timedelta(days=days)

        match data_type:
            case "exchange_rate":
                data = await self._service.get_exchange_rate(identifier or "USD", start_date)
            case "interest_rate":
                data = await self._service.get_interest_rate(identifier or "FED", start_date)
            case "gold":
                data = await self._service.get_gold_price(start_date)
            case "oil":
                data = await self._service.get_oil_price(identifier or "WTI", start_date)
            case "bonds":
                data = await self._service.get_bond_yield(identifier or "United States 10-Year", start_date)
            case "fear_greed":
                data = await self._service.get_fear_greed(start_date)
            case "business_indicator":
                data = await self._service.get_business_indicator(start_date)
            case _:
                return ToolResult(content=f"Unknown macro type: {data_type}", error="Invalid type")

        if not data:
            return ToolResult(content=f"無 {data_type} 資料")
        return ToolResult(
            content=f"{data_type}: {len(data)} 筆資料",
            data={"records": data[-10:]},
        )


class ScreenStocksTool:
    name = "screen_stocks"
    description = "Screen/filter stocks based on preset criteria (strong, trend, surge, bollinger breakout, etc.)"
    display_name_template = "篩選股票 ({screen_type})"
    parameters = {
        "type": "object",
        "properties": {
            "screen_type": {
                "type": "string",
                "enum": ["strong_5d", "strong_10d", "trend", "breakout_bollinger", "surge"],
                "description": "Screening preset type",
            },
            "trade_date": {"type": "string", "description": "Date to screen (YYYY-MM-DD, default today)"},
        },
        "required": ["screen_type"],
    }

    def __init__(self, screener_service: ScreenerService) -> None:
        self._service = screener_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        screen_type = args["screen_type"]
        trade_date_str = args.get("trade_date")
        trade_date = date.fromisoformat(trade_date_str) if trade_date_str else date.today()
        data = await self._service.run_screen(screen_type, trade_date)
        return ToolResult(
            content=f"篩選 {screen_type}: {len(data)} 檔符合",
            data={"records": data[:20], "total": len(data)},
        )


class GetIntlPriceTool:
    name = "get_intl_price"
    description = "Get price history for a European or Japanese index/stock (歐洲/日本指數). For US stocks use get_stock_history instead."
    display_name_template = "查詢國際行情 ({market})"
    parameters = {
        "type": "object",
        "properties": {
            "market": {"type": "string", "enum": ["europe", "japan"], "description": "Market region"},
            "stock_id": {"type": "string", "description": "Index/stock identifier for that market"},
            "days": {"type": "integer", "default": 30},
        },
        "required": ["market", "stock_id"],
    }

    def __init__(self, international_service: InternationalService) -> None:
        self._service = international_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        market = args["market"]
        stock_id = args["stock_id"]
        start_date = date.today() - timedelta(days=args.get("days", 30))
        if market == "europe":
            data = await self._service.get_europe_price(stock_id, start_date)
        elif market == "japan":
            data = await self._service.get_japan_price(stock_id, start_date)
        else:
            return ToolResult(content=f"不支援的市場: {market}", error="Invalid market")
        if not data:
            return ToolResult(content=f"{market} {stock_id}: 無行情資料")
        return ToolResult(
            content=f"{market} {stock_id}: {len(data)} 日行情",
            data={"records": data[-10:]},
        )


class GetFuturesAfterHoursTool:
    name = "get_futures_after_hours"
    description = "Get after-hours (夜盤) futures institutional positioning — overnight foreign/dealer net positions, an early signal for the next session."
    display_name_template = "查詢夜盤期貨法人"
    parameters = {
        "type": "object",
        "properties": {
            "contract": {"type": "string", "description": "Futures contract id (e.g. 'TX'); omit for all", "default": ""},
            "days": {"type": "integer", "default": 10},
        },
        "required": [],
    }

    def __init__(self, derivative_service: DerivativeService) -> None:
        self._service = derivative_service

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        contract = args.get("contract") or None
        start_date = date.today() - timedelta(days=args.get("days", 10))
        data = await self._service.get_futures_institutional_after_hours(contract, start_date)
        if not data:
            return ToolResult(content="無夜盤期貨法人資料")
        return ToolResult(
            content=f"夜盤期貨法人{f' ({contract})' if contract else ''}: {len(data)} 筆",
            data={"records": data[-10:]},
        )
