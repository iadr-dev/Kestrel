"""US-stock AI summary generator — parity with the TW summariser, but market-appropriate.

The TW generator (scripts/weekly_ai_summaries) is chip/籌碼-driven (三大法人/融資/集保),
which the US market doesn't have. This builds the US narrative from what US investors
actually watch — fundamentals (margins/valuation/growth), analyst consensus/target, and
price trend — and persists to the same ai_summaries table so the frontend is uniform.

Uses the same Gemini-via-OpenAI-compatible client as the TW path; rule-based fallback
when no LLM key is configured.
"""

import json
from datetime import date
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT = """You are a professional US equity analyst. Using ONLY the data below, produce an analysis summary for {ticker}.

Recent data:
- Last close: {close}
- 60-day trend (close series, oldest→newest): {trend}
- Up days in last 10 sessions: {up_days}/10
- Trailing P/E: {pe} | Forward P/E: {fpe}
- Net margin: {net_margin}% | Operating margin: {op_margin}%
- Revenue (TTM): {revenue}
- Analyst recommendation: {rec} | Mean target: {target} (current {close})
- Sector: {sector} | Industry: {industry}
- 52-week range: {low52} – {high52}

Output JSON:
{{
  "position_label": "bullish|cautiously bullish|neutral|cautiously bearish|bearish",
  "summary": "2-3 sentence professional analysis (English)",
  "factors": [
    {{"polarity": "positive|negative", "category": "fundamental|technical|analyst|valuation", "text": "specific factor", "importance": "key|normal"}}
  ],
  "swot": {{"strengths": ["1-2"], "weaknesses": ["1-2"], "opportunities": ["1-2"], "threats": ["1-2"]}}
}}

Rules: max 6 factors (≥2 key); base everything on the data, do not fabricate; concise SWOT.
"""


def _num(v: Any) -> float | None:
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


async def generate_us_summary(stock_id: str) -> dict[str, Any] | None:
    """Generate + persist a US-stock AI summary. Returns the summary dict, or None on
    total data failure (caller falls back to the score-synthesized summary)."""
    from app.providers.yfinance import YFinanceProvider
    yf = YFinanceProvider()
    try:
        hist = await yf.get_history(stock_id, period="3mo", interval="1d")
        info = await yf.get_info(stock_id)
    except Exception as e:
        logger.warning("us_summary_fetch_failed", stock_id=stock_id, error=str(e)[:120])
        return None
    if not info and not hist:
        return None

    closes: list[float] = [c for r in hist if (c := _num(r.get("Close", r.get("close")))) is not None]
    close = closes[-1] if closes else _num(info.get("_current"))
    up_days = sum(1 for i in range(max(1, len(closes) - 10), len(closes)) if closes[i] > closes[i - 1])
    trend = ", ".join(f"{c:.1f}" for c in closes[-12:]) if closes else "n/a"
    pm = _num(info.get("profit_margin"))
    om = _num(info.get("operating_margin"))

    ctx = {
        "ticker": stock_id,
        "close": f"{close:.2f}" if close else "n/a",
        "trend": trend,
        "up_days": up_days,
        "pe": info.get("pe_ratio") or "n/a",
        "fpe": info.get("forward_pe") or "n/a",
        "net_margin": f"{pm * 100:.1f}" if pm is not None else "n/a",
        "op_margin": f"{om * 100:.1f}" if om is not None else "n/a",
        "revenue": info.get("revenue") or "n/a",
        "rec": info.get("recommendation") or "n/a",
        "target": info.get("target_mean_price") or "n/a",
        "sector": info.get("sector") or "n/a",
        "industry": info.get("industry") or "n/a",
        "low52": info.get("52_week_low") or "n/a",
        "high52": info.get("52_week_high") or "n/a",
    }

    data = await _call_llm(ctx) or _fallback(stock_id, up_days, close, pm, info)
    await _persist(stock_id, data)
    return {"stock_id": stock_id, **data}


async def _call_llm(ctx: dict[str, Any]) -> dict[str, Any] | None:
    settings = Settings()
    if not settings.gemini_api_key:
        return None
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        resp = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": _PROMPT.format(**ctx)}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning("us_summary_llm_failed", ticker=ctx.get("ticker"), error=str(e)[:120])
        return None


def _fallback(stock_id: str, up_days: int, close: float | None, pm: float | None, info: dict[str, Any]) -> dict[str, Any]:
    """Rule-based summary when no LLM key is set."""
    profitable = pm is not None and pm > 0
    label = "cautiously bullish" if (up_days >= 7 and profitable) else "cautiously bearish" if up_days <= 3 else "neutral"
    return {
        "position_label": label,
        "summary": f"{stock_id} rose on {up_days}/10 recent sessions; last close {close:.2f}." if close else f"{stock_id} summary.",
        "factors": [
            {"polarity": "positive" if profitable else "negative", "category": "fundamental",
             "text": f"Net margin {pm * 100:.1f}%" if pm is not None else "Margin n/a", "importance": "key"},
            {"polarity": "positive" if (info.get("recommendation") or "").startswith(("buy", "strong")) else "neutral",
             "category": "analyst", "text": f"Analyst: {info.get('recommendation', 'n/a')}", "importance": "normal"},
        ],
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
    }


async def _persist(stock_id: str, data: dict[str, Any]) -> None:
    import asyncio

    from app.db.duckdb.engine import get_duckdb
    try:
        db = get_duckdb()

        def _w() -> None:
            with db.write_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ai_summaries (
                        stock_id VARCHAR NOT NULL, position_label VARCHAR, summary TEXT,
                        factors JSON, swot JSON, generated_at DATE NOT NULL, PRIMARY KEY (stock_id)
                    )
                """)
                conn.execute(
                    "INSERT OR REPLACE INTO ai_summaries "
                    "(stock_id, position_label, summary, factors, swot, generated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        stock_id, data.get("position_label", "neutral"), data.get("summary", ""),
                        json.dumps(data.get("factors", []), ensure_ascii=False),
                        json.dumps(data.get("swot", {}), ensure_ascii=False), str(date.today()),
                    ],
                )
        await asyncio.to_thread(_w)
    except Exception as e:
        logger.warning("us_summary_persist_failed", stock_id=stock_id, error=str(e)[:100])
