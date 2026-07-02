"""Rich card rendering tools — structured output for frontend components."""

from typing import Any

from app.agent.tools.base import ToolResult


class RenderStockCardTool:
    name = "render_stock_card"
    description = "Render a structured stock analysis card with price, chip, fundamental sections for rich UI display."
    display_name_template = "產生 {stock_id} 分析卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock ticker"},
            "stock_name": {"type": "string", "description": "Stock name"},
            "price_data": {
                "type": "object",
                "description": "Price section: current, change_pct, ma_status",
            },
            "chip_data": {
                "type": "object",
                "description": "Chip section: foreign_net, trust_net, dealer_net",
            },
            "fundamental_data": {
                "type": "object",
                "description": "Fundamental section: revenue_mom, revenue_yoy, eps",
            },
            "score": {"type": "number", "description": "Composite score 0-100"},
            "conclusion": {"type": "string", "description": "bullish/neutral/bearish"},
            "reasoning": {"type": "string", "description": "Brief reasoning for conclusion"},
        },
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"[RICH_CARD:stock_price] {args.get('stock_id')} analysis card rendered",
            data={
                "type": "rich_card",
                "card_type": "stock_analysis",
                **args,
            },
        )


class RenderComparisonTableTool:
    name = "render_comparison_table"
    description = "Render a side-by-side stock comparison table for multiple stocks."
    display_name_template = "產生比較表"
    parameters = {
        "type": "object",
        "properties": {
            "stocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stock_id": {"type": "string"},
                        "stock_name": {"type": "string"},
                        "metrics": {"type": "object"},
                    },
                },
                "description": "List of stocks with their comparison metrics",
            },
            "dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Comparison dimensions (e.g. 近月漲幅, 法人態度, 營收成長)",
            },
        },
        "required": ["stocks"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stocks = args.get("stocks", [])
        return ToolResult(
            content=f"[RICH_CARD:comparison_table] {len(stocks)} stocks compared",
            data={
                "type": "rich_card",
                "card_type": "comparison_table",
                **args,
            },
        )


class RenderScoreGaugeTool:
    name = "render_score_gauge"
    description = "Render an AI score gauge card showing 4-factor breakdown (technical, chip, fundamental, theme) for a stock."
    display_name_template = "產生 {stock_id} AI 評分卡"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "overall": {"type": "number", "description": "Overall score 0-100"},
            "technical": {"type": "number", "description": "Technical score 0-100"},
            "chip": {"type": "number", "description": "Chip/institutional score 0-100"},
            "fundamental": {"type": "number", "description": "Fundamental score 0-100"},
            "theme": {"type": "number", "description": "Theme/sector score 0-100"},
        },
        "required": ["stock_id", "overall"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"AI Score for {args['stock_id']}: {args.get('overall', 0)}/100",
            data={"type": "rich_card", "card_type": "score", **args},
        )


class RenderChartTool:
    name = "render_chart"
    description = "Render an inline mini chart (bar, line, or area) to visualize trends like revenue, institutional flow, price history."
    display_name_template = "產生圖表"
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Chart title"},
            "chart_type": {"type": "string", "enum": ["bar", "line", "area"]},
            "labels": {"type": "array", "items": {"type": "string"}, "description": "X-axis labels"},
            "values": {"type": "array", "items": {"type": "number"}, "description": "Data values"},
            "unit": {"type": "string", "description": "Unit label (e.g. 億, %, M)"},
        },
        "required": ["chart_type", "labels", "values"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Chart: {args.get('title', 'data')} ({len(args.get('values', []))} points)",
            data={"type": "rich_card", "card_type": "chart", **args},
        )


class RenderAlertConfirmTool:
    name = "render_alert_confirm"
    description = "Render an alert confirmation card after successfully creating a price/volume alert."
    display_name_template = "確認提醒設定"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "condition": {"type": "string", "description": "Alert condition description"},
            "threshold": {"type": "number"},
            "channels": {"type": "array", "items": {"type": "string"}},
            "alert_id": {"type": "string"},
        },
        "required": ["stock_id", "condition"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Alert set for {args['stock_id']}: {args['condition']}",
            data={"type": "rich_card", "card_type": "alert_confirm", **args},
        )


class RenderSupplyChainTool:
    name = "render_supply_chain"
    description = "Render a supply chain relationship card showing upstream suppliers, downstream customers, and competitors."
    display_name_template = "產生 {stock_id} 供應鏈卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "upstream": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}}}},
            "downstream": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}}}},
            "competitors": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}}},
        },
        "required": ["stock_id", "upstream", "downstream"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Supply chain for {args['stock_id']}: {len(args.get('upstream', []))} upstream, {len(args.get('downstream', []))} downstream",
            data={"type": "rich_card", "card_type": "supply_chain", **args},
        )


class RenderThemeOverviewTool:
    name = "render_theme_overview"
    description = "Render a theme/concept stock overview card with tier breakdown (upstream/midstream/downstream)."
    display_name_template = "產生 {theme_name} 題材卡片"
    parameters = {
        "type": "object",
        "properties": {
            "theme_id": {"type": "string"},
            "theme_name": {"type": "string"},
            "stock_count": {"type": "integer"},
            "today_change_pct": {"type": "number"},
            "tiers": {
                "type": "object",
                "properties": {
                    "upstream": {"type": "array", "items": {"type": "object"}},
                    "midstream": {"type": "array", "items": {"type": "object"}},
                    "downstream": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        "required": ["theme_id", "theme_name", "stock_count"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Theme: {args['theme_name']} ({args['stock_count']} stocks)",
            data={"type": "rich_card", "card_type": "theme_overview", **args},
        )


class RenderKlineChartTool:
    name = "render_kline_chart"
    description = (
        "Render a candlestick (K線) chart for a stock with OHLC bars, volume, and "
        "optional moving-average overlays. Use after fetching price data for any "
        "technical-analysis query instead of dumping numeric arrays as text."
    )
    display_name_template = "產生 {stock_id} K線圖"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "dates": {"type": "array", "items": {"type": "string"}, "description": "Date labels (oldest→newest)"},
            "open": {"type": "array", "items": {"type": "number"}},
            "high": {"type": "array", "items": {"type": "number"}},
            "low": {"type": "array", "items": {"type": "number"}},
            "close": {"type": "array", "items": {"type": "number"}},
            "volume": {"type": "array", "items": {"type": "number"}, "description": "Optional volume bars"},
            "overlays": {
                "type": "array",
                "description": "Optional MA/indicator lines: [{name:'MA20', values:[...]}]",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "values": {"type": "array", "items": {"type": "number"}},
                    },
                },
            },
        },
        "required": ["stock_id", "dates", "open", "high", "low", "close"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"K-line chart for {args['stock_id']} ({len(args.get('close', []))} bars)",
            data={"type": "rich_card", "card_type": "kline_chart", **args},
        )


class RenderInstitutionalFlowTool:
    name = "render_institutional_flow"
    description = (
        "Render an institutional net buy/sell trend card (三大法人買賣超) — grouped bars "
        "for 外資/投信/自營商 over time. Use for chip-flow analysis instead of a text table."
    )
    display_name_template = "產生 {stock_id} 法人買賣超圖"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "dates": {"type": "array", "items": {"type": "string"}, "description": "Date labels (oldest→newest)"},
            "foreign_net": {"type": "array", "items": {"type": "number"}, "description": "外資 net (張 or shares)"},
            "trust_net": {"type": "array", "items": {"type": "number"}, "description": "投信 net"},
            "dealer_net": {"type": "array", "items": {"type": "number"}, "description": "自營商 net"},
            "unit": {"type": "string", "description": "Unit label (e.g. 張, 股)", "default": "張"},
        },
        "required": ["stock_id", "dates"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Institutional flow for {args['stock_id']} ({len(args.get('dates', []))} days)",
            data={"type": "rich_card", "card_type": "institutional_flow_trend", **args},
        )


class RenderFinancialStatementTool:
    name = "render_financial_statement"
    description = (
        "Render a financial statement table (財報) — income statement, balance sheet, or "
        "cash flow across periods with key metrics. Use for fundamental analysis instead "
        "of a dense markdown table."
    )
    display_name_template = "產生 {stock_id} 財報表"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "statement_type": {"type": "string", "enum": ["income", "balance", "cashflow"], "description": "Statement kind"},
            "periods": {
                "type": "array",
                "description": "Per-period rows, e.g. [{period:'2025Q1', revenue, net_income, eps, margin_pct, yoy_pct}]",
                "items": {"type": "object"},
            },
            "unit": {"type": "string", "description": "Number unit (e.g. 億, 千元)", "default": "億"},
        },
        "required": ["stock_id", "statement_type", "periods"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"{args['statement_type']} statement for {args['stock_id']} ({len(args.get('periods', []))} periods)",
            data={"type": "rich_card", "card_type": "financial_statement", **args},
        )


class RenderDividendHistoryTool:
    name = "render_dividend_history"
    description = (
        "Render a dividend history card (配息紀錄) — per-year cash/stock dividends, "
        "ex-dates, and yield% with a yield trend. Use for dividend/income queries "
        "instead of a plain text table."
    )
    display_name_template = "產生 {stock_id} 配息卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "years": {
                "type": "array",
                "description": "Per-year rows: [{year, cash_dividend, stock_dividend, ex_date, yield_pct}]",
                "items": {"type": "object"},
            },
        },
        "required": ["stock_id", "years"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Dividend history for {args['stock_id']} ({len(args.get('years', []))} years)",
            data={"type": "rich_card", "card_type": "dividend_history", **args},
        )


class RenderShortPositionTool:
    name = "render_short_position"
    description = (
        "Render a short-position trend card (借券/融券) — short-sale and securities-"
        "lending balance over time. Rising balance = bearish positioning. Use for "
        "short-interest / contrarian analysis instead of numeric text."
    )
    display_name_template = "產生 {stock_id} 借券趨勢圖"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "dates": {"type": "array", "items": {"type": "string"}, "description": "Date labels (oldest→newest)"},
            "short_balance": {"type": "array", "items": {"type": "number"}, "description": "融券餘額 / short-sale balance"},
            "lending_balance": {"type": "array", "items": {"type": "number"}, "description": "借券餘額 / securities-lending balance"},
            "unit": {"type": "string", "description": "Unit label (e.g. 張, 股)", "default": "張"},
        },
        "required": ["stock_id", "dates"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Short position trend for {args['stock_id']} ({len(args.get('dates', []))} days)",
            data={"type": "rich_card", "card_type": "short_position_trend", **args},
        )


class RenderOptionsSentimentTool:
    name = "render_options_sentiment"
    description = (
        "Render an options sentiment card — put/call ratio and implied-volatility "
        "gauge with a fear/greed read. High put/call = fear (possible bottom); low = "
        "greed. Use for options/sentiment timing queries."
    )
    display_name_template = "產生選擇權情緒卡片"
    parameters = {
        "type": "object",
        "properties": {
            "put_call_ratio": {"type": "number", "description": "Put/Call ratio (P/C)"},
            "iv_rank": {"type": "number", "description": "IV rank 0-100 (optional)"},
            "current_iv": {"type": "number", "description": "Current implied volatility % (optional)"},
            "sentiment": {"type": "string", "enum": ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]},
            "note": {"type": "string", "description": "Short interpretation"},
        },
        "required": ["put_call_ratio"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Options sentiment: P/C {args.get('put_call_ratio')}, {args.get('sentiment', '')}",
            data={"type": "rich_card", "card_type": "options_sentiment", **args},
        )


class RenderEsgScorecardTool:
    name = "render_esg_scorecard"
    description = (
        "Render an ESG scorecard (ESG 評分) — overall score plus per-topic breakdown "
        "(greenhouse gas, energy, water, human development, governance). Use for "
        "ESG/sustainability queries instead of plain text."
    )
    display_name_template = "產生 {stock_id} ESG 評分卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "overall": {"type": "number", "description": "Overall ESG score (0-100)"},
            "topics": {
                "type": "array",
                "description": "Per-topic scores: [{name, score, unit}] e.g. 溫室氣體排放, 能源管理, 水資源, 人力發展, 公司治理",
                "items": {"type": "object"},
            },
        },
        "required": ["stock_id", "topics"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"ESG scorecard for {args['stock_id']} ({len(args.get('topics', []))} topics)",
            data={"type": "rich_card", "card_type": "esg_scorecard", **args},
        )


class RenderEtfProfileTool:
    name = "render_etf_profile"
    description = (
        "Render a Taiwan ETF profile card (ETF 概覽) — NAV / market price / 折溢價, 內扣費用 "
        "(expense ratio), 殖利率, Beta, top 成分股, and 產業分佈. Use after get_etf_data to "
        "show a rich card instead of plain text."
    )
    display_name_template = "產生 {etf_id} ETF 卡片"
    parameters = {
        "type": "object",
        "properties": {
            "etf_id": {"type": "string"},
            "name": {"type": "string"},
            "market_price": {"type": "number"},
            "nav": {"type": "number"},
            "premium_discount_pct": {"type": "number"},
            "expense_ratio_pct": {"type": "number", "description": "總費用率 (內扣)"},
            "yield_pct": {"type": "number"},
            "beta": {"type": "number"},
            "aum": {"type": "number", "description": "資產規模 (NT$)"},
            "holdings": {"type": "array", "description": "Top holdings: [{name, weight}]", "items": {"type": "object"}},
            "sectors": {"type": "array", "description": "Sector breakdown: [{industry, weight_pct}]", "items": {"type": "object"}},
        },
        "required": ["etf_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"ETF profile card for {args['etf_id']}",
            data={"type": "rich_card", "card_type": "etf_profile", **args},
        )


class RenderActiveEtfHoldersTool:
    name = "render_active_etf_holders"
    description = (
        "Render a 持有主動式ETF card — which active ETFs hold a stock, each with weight, "
        "持股張數 and 持股市值, plus the total. Use after get_active_etf_holders."
    )
    display_name_template = "產生 {stock_id} 主動式ETF持有卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "total_est_value": {"type": "number"},
            "holders": {
                "type": "array",
                "description": "[{etf_id, etf_name, weight_pct, shares_lots, est_value}]",
                "items": {"type": "object"},
            },
        },
        "required": ["stock_id", "holders"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content=f"Active-ETF holders card for {args['stock_id']} ({len(args.get('holders', []))} ETFs)",
            data={"type": "rich_card", "card_type": "active_etf_holders", **args},
        )


class RenderShareholderGiftTool:
    name = "render_shareholder_gift"
    description = (
        "Render a shareholder-gift card (股東紀念品) — gift item, 最後買進日, 股東會日期, 收購價 "
        "for one stock, or a list of upcoming gifts. Use after get_shareholder_gift."
    )
    display_name_template = "產生股東紀念品卡片"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string"},
            "stock_name": {"type": "string"},
            "gift_item": {"type": "string"},
            "last_buy_date": {"type": "string"},
            "meeting_date": {"type": "string"},
            "buyout_price": {"type": "number"},
            "gifts": {"type": "array", "description": "Upcoming-mode list: [{stock_id, stock_name, gift_item, last_buy_date, days_until}]", "items": {"type": "object"}},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(
            content="Shareholder gift card",
            data={"type": "rich_card", "card_type": "shareholder_gift", **args},
        )
