"""Figure Event Service — scans news via AI to auto-generate figure events."""

import json
import os
from datetime import date
from typing import Any, cast
from uuid import uuid4

import httpx

from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb

logger = get_logger(__name__)

FIGURE_NAMES = [
    "Jensen Huang", "Elon Musk", "Tim Cook", "Donald Trump",
    "Nancy Pelosi", "Jerome Powell", "Warren Buffett", "Cathie Wood",
    "Morris Chang", "Terry Gou", "C.C. Wei", "Lisa Su",
    "黃仁勳", "馬斯克", "川普", "裴洛西", "鮑爾", "巴菲特",
    "張忠謀", "郭台銘", "魏哲家", "蘇姿丰",
]

FIGURE_ID_MAP = {
    "Jensen Huang": "fig-jensen-huang", "黃仁勳": "fig-jensen-huang",
    "Elon Musk": "fig-elon-musk", "馬斯克": "fig-elon-musk",
    "Tim Cook": "fig-tim-cook", "提姆·庫克": "fig-tim-cook",
    "Donald Trump": "fig-trump", "川普": "fig-trump",
    "Nancy Pelosi": "fig-pelosi", "裴洛西": "fig-pelosi",
    "Jerome Powell": "fig-powell", "鮑爾": "fig-powell",
    "Kevin Warsh": "fig-kevin-warsh", "Kevin M. Warsh": "fig-kevin-warsh", "沃許": "fig-kevin-warsh",
    "Warren Buffett": "fig-buffett", "巴菲特": "fig-buffett",
    "Cathie Wood": "fig-cathie-wood", "木頭姐": "fig-cathie-wood",
    "Morris Chang": "fig-morris-chang", "張忠謀": "fig-morris-chang",
    "Terry Gou": "fig-terry-gou", "郭台銘": "fig-terry-gou",
    "C.C. Wei": "fig-cc-wei", "魏哲家": "fig-cc-wei",
    "Lisa Su": "fig-lisa-su", "蘇姿丰": "fig-lisa-su",
}


async def scan_figure_events() -> int:
    """Scan recent news for figure-related events using Gemini Flash."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("figure_scan_skipped", reason="no GEMINI_API_KEY")
        return 0

    news_items = await _fetch_recent_news()
    if not news_items:
        logger.info("figure_scan_no_news")
        return 0

    events = await _extract_events_with_ai(news_items, api_key)
    if not events:
        return 0

    inserted = _store_events(events)
    logger.info("figure_events_inserted", count=inserted)
    return inserted


async def _fetch_recent_news() -> list[dict[str, Any]]:
    """Fetch recent news from Alpha Vantage or Finnhub."""
    api_key = os.getenv("ALPHA_VANTAGE_KEY") or os.getenv("FINNHUB_KEY")
    if not api_key:
        return []

    news: list[dict[str, Any]] = []

    av_key = os.getenv("ALPHA_VANTAGE_KEY")
    if av_key:
        async with httpx.AsyncClient(timeout=30) as client:
            for keyword in ["NVDA", "TSLA", "AAPL", "SPY", "TSM"]:
                try:
                    resp = await client.get(
                        "https://www.alphavantage.co/query",
                        params={"function": "NEWS_SENTIMENT", "tickers": keyword, "limit": "10", "apikey": av_key},
                    )
                    data = resp.json()
                    for item in data.get("feed", [])[:5]:
                        news.append({
                            "title": item.get("title", ""),
                            "summary": item.get("summary", ""),
                            "source": item.get("source", ""),
                            "time": item.get("time_published", ""),
                            "tickers": [t["ticker"] for t in item.get("ticker_sentiment", [])],
                        })
                except Exception:
                    continue

    return news[:30]


async def _extract_events_with_ai(news: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    """Use Gemini Flash to extract figure events from news."""
    from pathlib import Path
    names_str = ", ".join(FIGURE_NAMES[:12])
    news_text = "\n".join([f"- [{n['time']}] {n['title']}: {n['summary'][:200]}" for n in news[:20]])

    prompt_path = Path(__file__).parent.parent / "app" / "agent" / "prompts" / "figure_extraction.md"
    if not prompt_path.exists():
        prompt_path = Path(__file__).parent / ".." / "agent" / "prompts" / "figure_extraction.md"
    template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else "Extract figure events from: {news_text}"
    prompt = template.replace("{figure_names}", names_str).replace("{news_text}", news_text)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                },
            )
            result = resp.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return cast(list[dict[str, Any]], json.loads(text))
    except Exception as e:
        logger.error("figure_ai_extraction_failed", error=str(e)[:200])
        return []


def _store_events(events: list[dict[str, Any]]) -> int:
    """Store extracted events in DuckDB, deduplicating by title similarity."""
    db = get_duckdb()
    cursor = db.read_connection()
    today = str(date.today())

    existing_titles = set()
    rows = cursor.execute(
        "SELECT title FROM figure_events WHERE event_date >= CURRENT_DATE - INTERVAL '3 days'"
    ).fetchall()
    for row in rows:
        existing_titles.add(row[0].lower()[:50])

    inserted = 0
    with db.write_connection() as conn:
        for evt in events:
            figure_name = evt.get("figure_name", "")
            figure_id = FIGURE_ID_MAP.get(figure_name)
            if not figure_id:
                continue

            title = evt.get("title", "")
            if title.lower()[:50] in existing_titles:
                continue

            conn.execute(
                "INSERT INTO figure_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid4()),
                    figure_id,
                    today,
                    evt.get("event_type", "speech"),
                    title,
                    evt.get("description"),
                    None,
                    evt.get("primary_stock_id"),
                    json.dumps(evt.get("affected_stocks", [])),
                    None, None, None,
                    evt.get("sentiment", "neutral"),
                    evt.get("importance", 5),
                ],
            )
            inserted += 1

    return inserted
