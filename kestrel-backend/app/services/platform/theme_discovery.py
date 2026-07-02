"""News/event-driven investment-theme discovery.

The base taxonomy comes from FinMind (see scripts/seed_themes.py). This module
catches *emerging* themes that structured data hasn't labeled yet — e.g. a new
IPO sector or a narrative forming across recent news.

Signal sources (all already in the backend):
- Recent market news (FinMind TaiwanStockNews)
- Figure events (figures pipeline — "Jensen Huang announces X")
- Hot stocks (DuckDB price_daily — volume/momentum surge)

Flow: gather signals → LLM proposes themes with member stocks + confidence →
dedup against existing themes (exact + fuzzy) → persist accepted themes/members
to DuckDB via ThemeRepository (status='active', source='llm_discovery').
Fully automated — no human approval gate, so accepted themes go live immediately
and are visible to the frontend. Provenance (source='llm_discovery') and the
theme_change_log keep every auto-created theme attributable and reversible.
"""

import json
from datetime import date, timedelta
from typing import Any, cast

from app.core.config import Settings
from app.core.constants import (
    THEME_MIN_CONFIDENCE as MIN_CONFIDENCE,
)
from app.core.constants import (
    THEME_MIN_MEMBERS as MIN_MEMBERS,
)
from app.core.constants import (
    FinMindDataset,
)
from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb
from app.services.data.theme_repository import ThemeRepository

logger = get_logger(__name__)

MODEL = "gemini-2.5-flash"

DISCOVERY_PROMPT = """你是專業的台灣股市產業分析師。根據以下近期市場訊號，找出「尚未被現有主題涵蓋」的新興投資主題。

現有主題（請勿重複，亦勿提出語意近似者）：
{existing_themes}

近期市場新聞標題：
{news}

近期人物/事件動態：
{events}

近期高成交量強勢股：
{hot_stocks}

任務：
1. 找出正在形成的新投資主題（例如新 IPO 帶動的題材、政策驅動的新賽道）。
2. 每個主題需對應實際存在的台股代號（至少 {min_members} 檔）。
3. 給出 0~1 的信心分數，反映訊號強度與主題真實性。
4. 不要編造股票代碼；不要重複現有主題。

輸出 JSON：
{{
  "themes": [
    {{
      "name_zh": "主題中文名",
      "name_en": "English name",
      "confidence": 0.0,
      "reason": "形成此主題的依據（引用上方訊號）",
      "stocks": [{{"stock_id": "1234", "sub_industry": "細分領域"}}]
    }}
  ]
}}
若無明顯新主題，回傳 {{"themes": []}}。
"""


def _canonical(name: str) -> str:
    """Normalize a theme name for dedup comparison."""
    return "".join(name.lower().split()).replace("股", "").replace("概念", "")


async def _gather_news(provider: Any, days: int) -> list[str]:
    start = date.today() - timedelta(days=days)
    rows = await provider.fetch(FinMindDataset.TAIWAN_STOCK_NEWS, start_date=start)
    titles = [r.get("title", "") for r in (rows or []) if r.get("title")]
    return titles[:60]


def _gather_events(limit: int = 30) -> list[str]:
    db = get_duckdb()
    try:
        rows = db.read_connection().execute(
            "SELECT title, event_date FROM figure_events ORDER BY event_date DESC LIMIT ?",
            [limit],
        ).fetchall()
    except Exception:
        return []
    return [f"{r[1]}: {r[0]}" for r in rows if r[0]]


def _gather_hot_stocks(limit: int = 30) -> list[str]:
    db = get_duckdb()
    try:
        rows = db.read_connection().execute("""
            WITH recent AS (
                SELECT stock_id, close, date, volume,
                       FIRST(close) OVER (PARTITION BY stock_id ORDER BY date) AS first_close,
                       LAST(close) OVER (PARTITION BY stock_id ORDER BY date) AS last_close
                FROM price_daily
                WHERE date >= CURRENT_DATE - INTERVAL '5 days'
            )
            SELECT stock_id,
                   (MAX(last_close) - MIN(first_close)) / NULLIF(MIN(first_close), 0) * 100 AS chg,
                   SUM(volume) AS vol
            FROM recent GROUP BY stock_id ORDER BY vol DESC LIMIT ?
        """, [limit]).fetchall()
    except Exception:
        return []
    return [f"{r[0]}: {r[1]:.1f}%" for r in rows if r[1] is not None]


async def _call_llm(prompt: str, settings: Settings) -> dict[str, Any]:
    import openai
    client = openai.AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return cast(dict[str, Any], json.loads(resp.choices[0].message.content or "{}"))


def _is_duplicate(name_zh: str, existing_canon: set[str]) -> bool:
    canon = _canonical(name_zh)
    if canon in existing_canon:
        return True
    # Substring overlap either direction → treat as duplicate.
    return any(canon and (canon in e or e in canon) for e in existing_canon)


async def discover_themes(days: int = 7) -> dict[str, Any]:
    """Run one discovery pass. Returns a summary dict."""
    settings = Settings()
    if not settings.gemini_api_key:
        logger.warning("theme_discovery_skipped", reason="no_gemini_key")
        return {"proposed": 0, "skipped": "no_llm_key"}

    repo = ThemeRepository()
    existing_names = repo.list_theme_names_sync()
    existing_canon = {_canonical(n) for n in existing_names}

    from app.providers.finmind.provider import FinMindProvider
    provider = FinMindProvider(settings)
    await provider.initialize()
    try:
        news = await _gather_news(provider, days)
    finally:
        await provider.close()

    events = _gather_events()
    hot = _gather_hot_stocks()

    if not news and not events and not hot:
        logger.warning("theme_discovery_no_signals")
        return {"proposed": 0, "skipped": "no_signals"}

    prompt = DISCOVERY_PROMPT.format(
        existing_themes=", ".join(existing_names[:60]) or "（無）",
        news="\n".join(f"- {t}" for t in news) or "（無）",
        events="\n".join(f"- {e}" for e in events) or "（無）",
        hot_stocks="\n".join(f"- {h}" for h in hot) or "（無）",
        min_members=MIN_MEMBERS,
    )

    try:
        result = await _call_llm(prompt, settings)
    except Exception as e:
        logger.warning("theme_discovery_llm_failed", error=str(e)[:120])
        return {"proposed": 0, "error": "llm_failed"}

    proposed = 0
    # One transaction for all accepted themes + their memberships (the per-row
    # upserts nest into this outer write_connection) — one commit, not per row.
    with get_duckdb().write_connection():
        for theme in result.get("themes", []):
            name_zh = (theme.get("name_zh") or "").strip()
            stocks = theme.get("stocks", [])
            confidence = float(theme.get("confidence", 0))

            if not name_zh or len(stocks) < MIN_MEMBERS or confidence < MIN_CONFIDENCE:
                continue
            if _is_duplicate(name_zh, existing_canon):
                logger.info("theme_discovery_duplicate_skipped", name=name_zh)
                continue

            # No approval gate: accepted themes go live immediately. Provenance is
            # preserved via source='llm_discovery' and the theme_change_log entry,
            # so any auto-created theme stays attributable and reversible.
            repo.upsert_theme(
                theme_id=name_zh, name_zh=name_zh, name_en=theme.get("name_en", ""),
                status="active", source="llm_discovery",
            )
            for s in stocks:
                sid = str(s.get("stock_id", "")).strip()
                if sid:
                    repo.upsert_membership(
                        stock_id=sid, theme_id=name_zh, sub_industry=s.get("sub_industry", ""),
                        confidence=confidence, source="llm_discovery",
                    )
            existing_canon.add(_canonical(name_zh))
            proposed += 1
            logger.info("theme_discovered", name=name_zh, members=len(stocks), confidence=confidence)

    logger.info("theme_discovery_complete", proposed=proposed)
    return {"proposed": proposed, "news_signals": len(news), "event_signals": len(events)}
