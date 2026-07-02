"""Weekly AI summary generation — creates stock analysis text using LLM.

Runs weekly (Sunday 02:00 TW) for top stocks.
Uses Gemini Flash for cost efficiency (~$0.002 per stock).
Results stored in DuckDB for the stock detail "產業分析" tab.

Usage: python -m scripts.weekly_ai_summaries
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb

logger = get_logger(__name__)

ANALYSIS_PROMPT = """你是專業的台灣股市分析師。根據以下資料，為 {stock_id} 產出分析摘要。

近期資料:
- 近60日收盤走勢: {price_trend}
- 近10日漲跌天數: {up_days}/10 天上漲
- 最新收盤價: {close}
- 近月營收年增率: {revenue_yoy}%
- 三大法人近20日買賣: 淨買{inst_net}
- 融資餘額近20日變化: {margin_trend}
- 最新季度 EPS: {eps}, 淨利率: {net_margin}%
- 集保大戶持股比例變化: {tdcc_trend}
- 近期重大訊息/法說會: {material_events}
- 所屬產業: {theme}

輸出 JSON:
{{
  "position_label": "短期偏多|中期偏多|中期觀望|短期偏空|中期偏空",
  "summary": "2-3句話的專業分析摘要（繁體中文）",
  "factors": [
    {{"polarity": "positive|negative", "category": "fundamental|technical|chips|theme", "text": "具體因素描述", "importance": "key|normal"}}
  ],
  "swot": {{
    "strengths": ["1-2項優勢"],
    "weaknesses": ["1-2項劣勢"],
    "opportunities": ["1-2項機會"],
    "threats": ["1-2項威脅"]
  }}
}}

規則:
- 最多6個factors（至少2個key）
- 必須基於提供的數據，不要編造
- 使用繁體中文
- SWOT各項1-2條，精簡有力
"""


async def generate_summaries(stock_ids: list[str] | None = None, max_stocks: int = 50):
    """Generate AI analysis summaries for top stocks using LLM."""
    settings = Settings()
    db = get_duckdb()
    cursor = db.read_connection()

    # Ensure ai_summaries table exists
    with db.write_connection() as wconn:
        wconn.execute("""
            CREATE TABLE IF NOT EXISTS ai_summaries (
                stock_id VARCHAR NOT NULL,
                position_label VARCHAR,
                summary TEXT,
                factors JSON,
                swot JSON,
                generated_at DATE NOT NULL,
                PRIMARY KEY (stock_id)
            )
        """)

    if stock_ids is None:
        rows = cursor.execute("""
            SELECT stock_id, SUM(volume) as vol FROM price_daily
            WHERE date >= CURRENT_DATE - INTERVAL '5 days'
            GROUP BY stock_id
            ORDER BY vol DESC
            LIMIT ?
        """, [max_stocks]).fetchall()
        stock_ids = [r[0] for r in rows]

    # Load theme memberships from DuckDB (migrated off the old JSON file).
    theme_map: dict[str, str] = {}
    try:
        trows = cursor.execute(
            "SELECT stock_id, theme_id FROM theme_memberships WHERE removed_at IS NULL"
        ).fetchall()
        theme_map = {r[0]: r[1] for r in trows}
    except Exception:
        pass

    logger.info("summary_generation_start", stocks=len(stock_ids))

    # Setup LLM client (Gemini Flash via OpenAI-compatible)
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        model = "gemini-2.5-flash"
    except (ImportError, Exception):
        logger.warning("llm_unavailable_falling_back_to_rules")
        client = None
        model = None

    summaries = []
    for stock_id in stock_ids:
        try:
            # Gather context from DuckDB
            prices = cursor.execute("""
                SELECT date, close FROM price_daily
                WHERE stock_id = ? AND date >= CURRENT_DATE - INTERVAL '60 days'
                ORDER BY date
            """, [stock_id]).fetchall()

            if len(prices) < 10:
                continue

            closes = [r[1] for r in prices]
            close = closes[-1]
            up_days = sum(1 for i in range(1, min(11, len(closes))) if closes[-i] > closes[-i-1]) if len(closes) > 1 else 5

            # Revenue
            rev = cursor.execute("""
                SELECT revenue_yoy FROM revenue_monthly
                WHERE stock_id = ? ORDER BY date DESC LIMIT 1
            """, [stock_id]).fetchone()
            revenue_yoy = round(rev[0], 1) if rev and rev[0] else 0

            # Institutional net
            inst = cursor.execute("""
                SELECT SUM(buy - sell) FROM institutional_daily
                WHERE stock_id = ? AND date >= CURRENT_DATE - INTERVAL '20 days'
            """, [stock_id]).fetchone()
            inst_net = inst[0] if inst and inst[0] else 0

            # Margin balance trend (融資, 20-day change %) — contrarian retail signal.
            margin_trend = "無資料"
            try:
                mrows = cursor.execute("""
                    SELECT margin_balance FROM margin_daily
                    WHERE stock_id = ? AND date >= CURRENT_DATE - INTERVAL '20 days'
                    ORDER BY date
                """, [stock_id]).fetchall()
                if len(mrows) >= 2 and mrows[0][0]:
                    chg = (mrows[-1][0] - mrows[0][0]) / mrows[0][0] * 100
                    margin_trend = f"{'增' if chg >= 0 else '減'}{abs(chg):.1f}%"
            except Exception:
                pass

            # Quarterly EPS + net margin (profitability).
            eps, net_margin = "無資料", "無資料"
            try:
                frow = cursor.execute("""
                    SELECT eps, net_margin FROM financials_quarterly
                    WHERE stock_id = ? ORDER BY date DESC LIMIT 1
                """, [stock_id]).fetchone()
                if frow:
                    eps = f"{frow[0]:.2f}" if frow[0] is not None else "無資料"
                    net_margin = f"{frow[1]:.1f}" if frow[1] is not None else "無資料"
            except Exception:
                pass

            # TDCC big-holder concentration trend (>400張 大戶 share, latest vs prior week).
            tdcc_trend = "無資料"
            try:
                from app.providers.tdcc import get_tdcc_client
                rows_t = await get_tdcc_client().get_shareholding(stock_id)
                # Rows are per holding-tier per date; isolate the ">400張" big-holder
                # tier and compare its share % across the two most recent dates.
                big = [r for r in rows_t if "400" in str(r.get("level", r.get("HoldingSharesLevel", "")))]
                if len(big) >= 2:
                    big.sort(key=lambda r: str(r.get("date", "")))
                    latest_pct = float(big[-1].get("percent", big[-1].get("percentage", 0)) or 0)
                    prior_pct = float(big[-2].get("percent", big[-2].get("percentage", 0)) or 0)
                    delta = latest_pct - prior_pct
                    tdcc_trend = f"大戶持股{latest_pct:.1f}% ({'增' if delta >= 0 else '減'}{abs(delta):.2f}pp)"
            except Exception:
                pass

            # Recent figure events / material catalysts (from the figures pipeline).
            material_events = "無"
            try:
                erows = cursor.execute("""
                    SELECT title FROM figure_events
                    WHERE (primary_stock_id = ? OR affected_stocks LIKE ?)
                      AND event_date >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY event_date DESC LIMIT 3
                """, [stock_id, f'%{stock_id}%']).fetchall()
                if erows:
                    material_events = "; ".join(e[0] for e in erows if e[0])[:200] or "無"
            except Exception:
                pass

            # Analyst data from yfinance
            analyst_target = None
            analyst_rec = None
            try:
                from app.providers.yfinance import YFinanceProvider
                yf_provider = YFinanceProvider()
                yf_info = await yf_provider.get_info(stock_id)
                analyst_target = yf_info.get("target_mean_price")
                analyst_rec = yf_info.get("recommendation")
            except Exception:
                pass

            theme = theme_map.get(stock_id, "未分類")
            price_trend = f"{closes[0]:.1f} → {closes[-1]:.1f} ({'↑' if closes[-1] > closes[0] else '↓'}{abs(closes[-1] - closes[0]) / closes[0] * 100:.1f}%)"

            if client:
                analyst_str = ""
                if analyst_target:
                    analyst_str = f"\n- 分析師目標價: ${analyst_target:.1f}, 建議: {analyst_rec or 'N/A'}"
                prompt = ANALYSIS_PROMPT.format(
                    stock_id=stock_id,
                    price_trend=price_trend,
                    up_days=up_days,
                    close=close,
                    revenue_yoy=revenue_yoy,
                    inst_net=f"{inst_net:,.0f}",
                    margin_trend=margin_trend,
                    eps=eps,
                    net_margin=net_margin,
                    tdcc_trend=tdcc_trend,
                    material_events=material_events,
                    theme=theme,
                ) + analyst_str
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                data = json.loads(raw)
            else:
                # Rule-based fallback
                if up_days >= 7 and revenue_yoy > 10:
                    position = "短期偏多"
                elif up_days <= 3 and revenue_yoy < 0:
                    position = "短期偏空"
                else:
                    position = "中期觀望"

                data = {
                    "position_label": position,
                    "summary": f"{stock_id} 近10日有{up_days}天上漲，收盤價{close}，近月營收年增{revenue_yoy}%。",
                    "factors": [
                        {"polarity": "positive" if revenue_yoy > 0 else "negative", "category": "fundamental", "text": f"營收年增{revenue_yoy}%", "importance": "key"},
                        {"polarity": "positive" if inst_net > 0 else "negative", "category": "chips", "text": f"法人近20日淨買超{inst_net:,.0f}", "importance": "normal"},
                    ],
                    "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
                }

            # Store in DuckDB
            with db.write_connection() as wconn:
                wconn.execute("""
                    INSERT OR REPLACE INTO ai_summaries (stock_id, position_label, summary, factors, swot, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    stock_id,
                    data.get("position_label", "中期觀望"),
                    data.get("summary", ""),
                    json.dumps(data.get("factors", []), ensure_ascii=False),
                    json.dumps(data.get("swot", {}), ensure_ascii=False),
                    str(date.today()),
                ])

            summaries.append({"stock_id": stock_id, **data})
            logger.info("summary_generated", stock_id=stock_id, position=data.get("position_label"))

        except Exception as e:
            logger.warning("summary_failed", stock_id=stock_id, error=str(e)[:100])
            continue

    logger.info("summaries_complete", count=len(summaries))
    return summaries


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = asyncio.run(generate_summaries(max_stocks=20))
    print(f"Generated {len(result)} summaries")
