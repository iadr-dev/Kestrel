"""Agent tools powered by TWSE direct API — real-time quotes, institutional, disposal stocks, ESG, themes, ETF, OTC, options."""

from typing import Any

import httpx

from app.agent.tools.base import ToolResult
from app.providers.twse import get_twse_client


class GetRealtimeQuoteTool:
    name = "get_realtime_quote"
    description = "Get real-time intraday stock quotes from TWSE/OTC. Returns current price, volume, bid/ask. Works during trading hours (9:00-13:30 TW)."
    display_name_template = "查詢即時報價"
    parameters = {
        "type": "object",
        "properties": {
            "stock_ids": {"type": "string", "description": "Comma-separated stock codes (e.g. '2330,2454,2317')"},
        },
        "required": ["stock_ids"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_twse_client()
        codes = [c.strip() for c in args["stock_ids"].split(",")]
        data = await client.get_realtime_quote(codes)

        if not data:
            return ToolResult(content="目前無法取得即時報價（可能非交易時間）", data=[])

        lines = []
        for q in data:
            code = q.get("c", "")
            name = q.get("n", "")
            price = q.get("z", "-")
            volume = q.get("v", "0")
            high = q.get("h", "-")
            low = q.get("l", "-")
            change = ""
            if q.get("z") and q.get("y"):
                try:
                    diff = float(q["z"]) - float(q["y"])
                    pct = (diff / float(q["y"])) * 100
                    change = f" {'▲' if diff >= 0 else '▼'}{abs(diff):.2f} ({pct:+.2f}%)"
                except (ValueError, ZeroDivisionError):
                    pass
            lines.append(f"{name}({code}): ${price}{change} | 量:{volume}張 | 高:{high} 低:{low}")

        return ToolResult(content="\n".join(lines), data=data)


class GetNoticeStocksTool:
    name = "get_notice_stocks"
    description = "Get today's 注意股 (attention/warning stocks) list from TWSE. Shows stocks flagged for abnormal trading activity."
    display_name_template = "查詢注意股"
    parameters = {
        "type": "object",
        "properties": {},
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_twse_client()
        data = await client.fetch_openapi("/announcement/notice")

        if not data:
            return ToolResult(content="今日無注意股公告", data=[])

        lines = [f"今日注意股 ({len(data)} 檔):"]
        for item in data[:15]:
            code = item.get("股票代號", item.get("Code", ""))
            name = item.get("股票名稱", item.get("Name", ""))
            reason = item.get("注意事項", item.get("reason", ""))
            lines.append(f"  {code} {name} — {reason[:50]}")

        if len(data) > 15:
            lines.append(f"  ... 共 {len(data)} 檔")

        return ToolResult(content="\n".join(lines), data=data)


class GetDisposalStocksTool:
    name = "get_disposal_stocks"
    description = "Get 處置股 (disposition/disciplinary stocks) from TWSE. Shows stocks with trading restrictions (5-min/20-min batch auction)."
    display_name_template = "查詢處置股"
    parameters = {
        "type": "object",
        "properties": {},
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_twse_client()
        data = await client.fetch_openapi("/announcement/punish")

        if not data:
            return ToolResult(content="目前無處置股", data=[])

        lines = [f"處置股清單 ({len(data)} 檔):"]
        for item in data[:10]:
            code = item.get("股票代號", item.get("Code", ""))
            name = item.get("股票名稱", item.get("Name", ""))
            period = item.get("處置期間", "")
            lines.append(f"  {code} {name} | {period}")

        return ToolResult(content="\n".join(lines), data=data)


class GetTWSEInstitutionalTool:
    name = "get_twse_institutional"
    description = "Get institutional investor (三大法人) buy/sell summary from TWSE directly. Shows top stocks by net institutional trading. More comprehensive than FinMind data."
    display_name_template = "查詢TWSE法人買賣"
    parameters = {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "Date in YYYYMMDD format (optional, defaults to today)"},
            "limit": {"type": "integer", "description": "Number of top stocks to return (default 20)"},
        },
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_twse_client()
        date = args.get("date")
        limit = args.get("limit", 20)
        data = await client.get_institutional_summary(date, limit)

        if not data:
            return ToolResult(content="無法取得法人買賣超資料（可能非交易日）", data=[])

        lines = [f"三大法人買賣超 Top {limit}:"]
        for item in data[:limit]:
            code = item.get("證券代號", "").strip()
            name = item.get("證券名稱", "").strip()
            net = item.get("三大法人買賣超股數", "0")
            foreign = item.get("外陸資買賣超股數(不含外資自營商)", "0")
            trust = item.get("投信買賣超股數", "0")
            lines.append(f"  {code} {name} | 合計:{net} | 外資:{foreign} | 投信:{trust}")

        return ToolResult(content="\n".join(lines), data=data)


class GetFuturesPositionTool:
    name = "get_futures_position"
    description = "Get TAIFEX futures institutional positions and put/call ratio. Shows foreign investor futures/options positioning."
    display_name_template = "查詢期貨法人部位"
    parameters = {
        "type": "object",
        "properties": {},
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        client = get_twse_client()
        data = await client.get_futures_institutional()

        if not data:
            return ToolResult(content="無法取得期貨法人資料", data=[])

        lines = ["期貨三大法人:"]
        for item in data[:10]:
            name = item.get("身份別", item.get("IdentityType", ""))
            long_oi = item.get("多方未平倉口數", item.get("LongOI", ""))
            short_oi = item.get("空方未平倉口數", item.get("ShortOI", ""))
            net = item.get("多空未平倉淨額", item.get("NetOI", ""))
            lines.append(f"  {name} | 多:{long_oi} | 空:{short_oi} | 淨:{net}")

        return ToolResult(content="\n".join(lines), data=data)


class GetCompanyProfileTool:
    name = "get_company_profile"
    description = "Get company basic profile from TWSE — industry, address, capital, chairman, listed date."
    display_name_template = "Fetching company profile"
    parameters = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Stock code (e.g. '2330')"}},
        "required": ["code"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        # Normalized profile covers both listed (t187ap03_L) and OTC
        # (mopsfin_t187ap03_O) companies — replaces the retired MOPS scraper.
        data = await get_twse_client().get_company_profile(args["code"])
        if not data:
            return ToolResult(content=f"{args['code']}: No company profile found")
        lines = [f"{k}: {v}" for k, v in data.items() if v and str(v).strip()]
        return ToolResult(content="\n".join(lines[:20]), data=data)


class GetSupplyChainTool:
    name = "get_supply_chain"
    description = "Get supply chain relationships for a stock — upstream suppliers, downstream customers, competitors."
    display_name_template = "Fetching supply chain"
    parameters = {
        "type": "object",
        "properties": {"stock_id": {"type": "string", "description": "Stock code (e.g. '2330')"}},
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        stock_id = args["stock_id"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"http://localhost:8000/api/v1/themes/supply-chain/stock/{stock_id}")
                data = resp.json().get("data", [])
        except Exception:
            data = []
        if not data:
            return ToolResult(content=f"{stock_id}: No supply chain data available")
        lines = [f"Supply chain for {stock_id} ({len(data)} relationships):"]
        for r in data[:15]:
            lines.append(f"  {r.get('from', '')} -> {r.get('to', '')} ({r.get('type', '')})")
        return ToolResult(content="\n".join(lines), data={"count": len(data)})


class GetThemeStocksTool:
    name = "get_theme_stocks"
    description = "Get stocks in a theme/sector (e.g. semiconductor, AI, EV). Returns stock list with sub-industry."
    display_name_template = "Fetching theme stocks"
    parameters = {
        "type": "object",
        "properties": {"theme": {"type": "string", "description": "Theme name (e.g. 'semiconductor', 'AI', 'EV')"}},
        "required": ["theme"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        theme = args["theme"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("http://localhost:8000/api/v1/themes")
                themes = resp.json().get("data", [])
        except Exception:
            return ToolResult(content="Unable to fetch themes")
        matched = next((t for t in themes if theme.lower() in t.get("name_zh", "").lower() or theme.lower() in t.get("name_en", "").lower()), None)
        if not matched:
            return ToolResult(content=f"Theme '{theme}' not found. Available: {', '.join(t.get('name_zh', '') for t in themes[:10])}")
        return ToolResult(content=f"{matched['name_zh']} ({matched.get('stock_count', 0)} stocks)", data=matched)


class GetETFDataTool:
    name = "get_etf_data"
    description = (
        "Get a full profile for a Taiwan-listed ETF (0050, 0056, 00878, 主動式ETF like "
        "00407A, etc.): real-time NAV / market price / 折溢價 (premium-discount), plus 內扣"
        "費用 (expense ratio), 殖利率 (yield), Beta, 成分股 (top holdings), 產業分佈 (sector "
        "breakdown), and 配息紀錄 (dividend history). Use for any question about an ETF's "
        "cost, holdings, sectors, dividends, or risk."
    )
    display_name_template = "查詢{code}ETF資料"
    parameters = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "ETF code (e.g. '0050', '0056', '00878', '00407A')"}},
        "required": ["code"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        from app.providers.cache import InMemoryCache
        from app.scrapers.cmoney_etf import scrape_cmoney_etf
        from app.scrapers.twse_etf import scrape_etf_nav
        from app.services.data.active_etf_service import get_sector_breakdown

        code = args["code"]
        cache = InMemoryCache()

        try:
            all_etf = await scrape_etf_nav()
            nav_row = next((e for e in all_etf if e.get("etf_id") == code), {})
        except Exception:
            nav_row = {}
        try:
            cm = await scrape_cmoney_etf(code)
        except Exception:
            cm = {}
        try:
            sectors = (await get_sector_breakdown(cache, code)).get("sectors", [])
        except Exception:
            sectors = []

        if not nav_row and not cm:
            return ToolResult(content=f"{code}: 無ETF資料")

        name = nav_row.get("name") or code
        price = nav_row.get("market_price")
        nav = nav_row.get("estimated_nav")
        holdings = cm.get("top_holdings") or []
        dividends = cm.get("dividends") or []

        def _f(v: Any) -> float | None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        lines = [f"{name} ({code})"]
        if price or nav:
            pd_f = _f(nav_row.get("premium_discount_pct"))
            lines.append(f"市價: ${price} | 淨值: ${nav}" + (f" | 折溢價: {pd_f:+.2f}%" if pd_f is not None else ""))
        if cm.get("expense_ratio_pct") is not None:
            lines.append(f"總費用率(內扣): {cm['expense_ratio_pct']}% (管理費 {cm.get('management_fee_pct', '—')}% + 保管費 {cm.get('custody_fee_pct', '—')}%)")
        if cm.get("yield_pct") is not None:
            lines.append(f"殖利率: {cm['yield_pct']}% | Beta: {cm.get('beta', '—')} | 追蹤誤差: {cm.get('tracking_error_pct', '—')}%")
        if holdings:
            top = "、".join(f"{h['name']} {h['weight']}%" for h in holdings[:5])
            lines.append(f"前五大成分股: {top}")
        if sectors:
            secs = "、".join(f"{s['industry']} {s['weight_pct']}%" for s in sectors[:3])
            lines.append(f"產業分佈: {secs}")
        if dividends:
            d0 = dividends[0]
            lines.append(f"最近配息: {d0.get('ex_date')} 配 {d0.get('cash_dividend')} (殖利率 {d0.get('yield_pct')}%)")

        data: dict[str, Any] = {**nav_row, **cm, "sectors": sectors}
        return ToolResult(content="\n".join(lines), data=data)


class GetActiveEtfHoldersTool:
    name = "get_active_etf_holders"
    description = (
        "Get which 主動式ETF (Taiwan active ETFs) hold a given stock, and how much "
        "(持有主動式ETF). Returns each active ETF holding the stock with its weight, 持股張數, "
        "and estimated 持股市值, plus the total. Use for questions like '哪些主動式ETF持有台積電' "
        "or '2330 被多少主動式ETF持有'."
    )
    display_name_template = "查詢{stock_id}的主動式ETF持有"
    parameters = {
        "type": "object",
        "properties": {"stock_id": {"type": "string", "description": "Stock code (e.g. '2330', '2049')"}},
        "required": ["stock_id"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        from app.providers.cache import InMemoryCache
        from app.services.data.active_etf_service import get_active_holders

        stock_id = args["stock_id"]
        try:
            result = await get_active_holders(InMemoryCache(), stock_id)
        except Exception as e:
            return ToolResult(content=f"{stock_id}: 查詢主動式ETF持有失敗 ({str(e)[:60]})")

        holders = result.get("holders", [])
        if not holders:
            return ToolResult(content=f"{stock_id}: 目前沒有主動式ETF持有")

        total = result.get("total_est_value")
        lines = [f"{stock_id} 被 {len(holders)} 檔主動式ETF持有" + (f"，總持股市值約 {total / 1e8:.1f} 億" if total else "")]
        for h in holders:
            val = f" 約{h['est_value'] / 1e8:.2f}億" if h.get("est_value") else ""
            lots = f" {h['shares_lots']:,.0f}張" if h.get("shares_lots") else ""
            lines.append(f"  {h['etf_id']} {h.get('etf_name', '')}: {h.get('weight_pct', '—')}%{lots}{val}")
        return ToolResult(content="\n".join(lines), data=result)


class GetShareholderGiftTool:
    name = "get_shareholder_gift"
    description = (
        "Get Taiwan shareholder-meeting gift (股東紀念品) info. Two modes: pass `stock_id` "
        "for one stock's gift (gift item, 最後買進日, 股東會日期, 收購價), or pass `upcoming=true` "
        "for the list of gifts whose 最後買進日 is within the next N `days` (buy-before-date "
        "opportunities). Use for '台積電有股東紀念品嗎' or '最近有哪些股東紀念品可以領'."
    )
    display_name_template = "查詢股東紀念品"
    parameters = {
        "type": "object",
        "properties": {
            "stock_id": {"type": "string", "description": "Stock code for a single-stock lookup (e.g. '1101')"},
            "upcoming": {"type": "boolean", "description": "If true, list gifts with an approaching 最後買進日"},
            "days": {"type": "integer", "description": "Window in days for upcoming mode (default 30)"},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        from datetime import date

        from app.scrapers.shareholder_gifts import scrape_shareholder_gifts

        try:
            gifts = await scrape_shareholder_gifts()
        except Exception as e:
            return ToolResult(content=f"查詢股東紀念品失敗 ({str(e)[:60]})")

        stock_id = args.get("stock_id")
        if stock_id and not args.get("upcoming"):
            g = next((x for x in gifts if x.get("stock_id") == stock_id), None)
            if not g:
                return ToolResult(content=f"{stock_id}: 目前無股東紀念品")
            lines = [
                f"{g.get('stock_name', '')} ({stock_id}) 股東紀念品",
                f"紀念品: {g.get('gift_item', '—')}",
                f"最後買進日: {g.get('last_buy_date', '—')} | 股東會: {g.get('meeting_date', '—')}",
            ]
            if g.get("buyout_price") is not None:
                lines.append(f"平台收購價: {g['buyout_price']}")
            return ToolResult(content="\n".join(lines), data=g)

        # Upcoming mode (default when no stock_id, or upcoming=true).
        days = args.get("days") or 30
        today = date.today()
        upcoming = []
        for g in gifts:
            lbd = g.get("last_buy_date")
            if not lbd:
                continue
            try:
                d = date.fromisoformat(lbd)
            except ValueError:
                continue
            delta = (d - today).days
            if 0 <= delta <= days:
                upcoming.append({**g, "days_until": delta})
        upcoming.sort(key=lambda x: x["days_until"])
        if not upcoming:
            return ToolResult(content=f"未來 {days} 天內沒有可參加的股東紀念品（多在 5–8 月股東會旺季）")
        lines = [f"未來 {days} 天內可參加的股東紀念品（{len(upcoming)} 檔）:"]
        for g in upcoming[:20]:
            lines.append(f"  {g['stock_id']} {g.get('stock_name', '')}: {g.get('gift_item', '—')} (最後買進 {g['last_buy_date']}, {g['days_until']}天)")
        return ToolResult(content="\n".join(lines), data={"count": len(upcoming), "gifts": upcoming})


class GetOTCStockTool:
    name = "get_otc_stock"
    description = "Get OTC (TPEx) stock daily data for stocks listed on the over-the-counter market."
    display_name_template = "Fetching OTC stock"
    parameters = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "OTC stock code (e.g. '6488')"}},
        "required": ["code"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().get_otc_daily(args["code"], limit=1)
        if not data:
            return ToolResult(content=f"{args['code']}: No OTC data found")
        lines = [f"OTC {args['code']}:"] + [f"  {k}: {v}" for k, v in data[0].items() if v][:8]
        return ToolResult(content="\n".join(lines), data=data[0])


class GetPutCallRatioTool:
    name = "get_put_call_ratio"
    description = "Get options put/call ratio from TAIFEX — market sentiment indicator (high=bearish, low=bullish)."
    display_name_template = "Fetching put/call ratio"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().get_put_call_ratio()
        if not data:
            return ToolResult(content="Unable to fetch put/call ratio")
        lines = ["Put/Call Ratio:"] + [f"  {item}" for item in data[:5]]
        return ToolResult(content="\n".join(lines), data={"count": len(data)})


class GetOptionsAnalyticsTool:
    name = "get_options_analytics"
    description = "Get options analytics from TAIFEX — delta, open interest changes, max pain."
    display_name_template = "Fetching options analytics"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().get_options_analytics()
        if not data:
            return ToolResult(content="Unable to fetch options analytics")
        lines = ["Options Analytics:"] + [f"  {item}" for item in data[:8]]
        return ToolResult(content="\n".join(lines), data={"count": len(data)})


class GetBacktestResultTool:
    name = "get_backtest_result"
    description = "Get backtest results for a strategy — win rate and returns. Strategies: ma_golden_cross, kd_low_cross, breakout_20d, inst_buy_3d."
    display_name_template = "Fetching backtest"
    parameters = {
        "type": "object",
        "properties": {"strategy": {"type": "string", "description": "Strategy ID (ma_golden_cross, kd_low_cross, breakout_20d, inst_buy_3d)"}},
        "required": ["strategy"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("http://localhost:8000/api/v1/screener/backtest", params={"strategy": args["strategy"]})
                result = resp.json()
        except Exception:
            return ToolResult(content=f"Unable to fetch backtest for {args['strategy']}")
        data = result.get("data", [])
        if not data:
            return ToolResult(content=f"No backtest results for: {args['strategy']}")
        lines = [f"Backtest: {args['strategy']} (top 5):"]
        for item in data[:5]:
            lines.append(f"  {item.get('k', '')} | 5D:{item.get('r5', 0):.1f}% | 20D:{item.get('r20', 0):.1f}% | Win:{item.get('win', 0):.0f}%")
        return ToolResult(content="\n".join(lines), data={"count": len(data)})


class GetCompanyESGTool:
    name = "get_company_esg"
    description = "Get ESG data from TWSE. Topics: 1=greenhouse gas, 2=energy, 3=water, 5=human dev, 9=governance."
    display_name_template = "Fetching ESG data"
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code (e.g. '2330')"},
            "topic": {"type": "integer", "description": "ESG topic (1-20, default 9=governance)"},
        },
        "required": ["code"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        topic = args.get("topic", 9)
        data = await get_twse_client().fetch_company(f"/opendata/t187ap46_L_{topic}", args["code"])
        if not data:
            return ToolResult(content=f"{args['code']}: No ESG data for topic {topic}")
        lines = [f"ESG Topic {topic} for {args['code']}:"]
        lines += [f"  {k}: {str(v)[:100]}" for k, v in data.items() if v and str(v).strip() and k != "公司代號"][:12]
        return ToolResult(content="\n".join(lines), data=data)


class GetWarrantInfoTool:
    name = "get_warrant_info"
    description = "Get warrant information — warrant code, underlying stock, strike price, expiry."
    display_name_template = "Fetching warrant info"
    parameters = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Warrant or underlying stock code"}},
        "required": ["code"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().fetch_openapi("/opendata/t187ap37_L")
        filtered = [d for d in data if args["code"] in str(d.get("權證代號", "")) or args["code"] in str(d.get("標的證券代號", ""))]
        if not filtered:
            return ToolResult(content=f"No warrants found for {args['code']}")
        lines = [f"Warrants for {args['code']} ({len(filtered)} found):"]
        for w in filtered[:8]:
            lines.append(f"  {w.get('權證代號', '')} | {w.get('權證名稱', '')} | Strike: {w.get('履約價', '')}")
        return ToolResult(content="\n".join(lines), data={"count": len(filtered)})


class GetMarketHolidaysTool:
    name = "get_market_holidays"
    description = "Get Taiwan stock market holiday schedule for the current year."
    display_name_template = "Fetching market holidays"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().fetch_openapi("/holidaySchedule/holidaySchedule")
        if not data:
            return ToolResult(content="Unable to fetch holiday schedule")
        lines = ["Market Holidays:"] + [f"  {h.get('Date', '')} — {h.get('Name', h.get('HolidayCategory', ''))}" for h in data[:15]]
        return ToolResult(content="\n".join(lines), data={"count": len(data)})


class GetOddLotTool:
    name = "get_odd_lot"
    description = "Get after-hours odd-lot trading (盤後零股) quotes for the latest session — a gauge of retail participation."
    display_name_template = "查詢盤後零股"
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code to filter (optional)"},
            "limit": {"type": "integer", "default": 30},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().fetch_report_rows("TWT53U")
        code = args.get("code")
        if code:
            data = [d for d in data if d.get("證券代號") == code or d.get("Code") == code]
        if not data:
            return ToolResult(content="無盤後零股資料", data=[])
        limit = args.get("limit", 30)
        return ToolResult(content=f"盤後零股: {len(data)} 檔", data={"records": data[:limit]})


class GetDividendScheduleTool:
    name = "get_dividend_schedule"
    description = "Get the ex-dividend / ex-rights schedule (除權息行事曆) — upcoming dividend dates and reference-price adjustments."
    display_name_template = "查詢除權息行事曆"
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Stock code to filter (optional)"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": [],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        data = await get_twse_client().fetch_report_rows("TWT48U_ALL")
        code = args.get("code")
        if code:
            data = [d for d in data if d.get("股票代號") == code]
        if not data:
            return ToolResult(content="無除權息資料", data=[])
        limit = args.get("limit", 50)
        return ToolResult(content=f"除權息行事曆: {len(data)} 筆", data={"records": data[:limit]})
