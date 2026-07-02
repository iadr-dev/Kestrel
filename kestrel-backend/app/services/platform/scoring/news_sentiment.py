"""News sentiment + hype-vs-fundamentals divergence for TW stocks.

Two signals, both from the news_daily headlines we already ingest:
  1. news_score(0-100): lexicon sentiment over a stock's recent headlines. A light
     overlay factor (small weight) — deliberately NOT LLM-per-stock, so it's fast and
     free enough to run on-demand for any stock.
  2. divergence flag: when news is HOT (very positive) but the chip + fundamental
     picture disagrees, that's the classic retail-trap / 追高 shape — surfaced as an
     honest caveat in the summary. This is NOT a black-box "割韭菜 detector"; it's a
     transparent news-vs-smart-money divergence.

Lexicon is intentionally simple + auditable (positive/negative TW finance terms).
"""

from typing import Any

# Weighted TW-finance sentiment terms. Values are polarity magnitudes.
_POSITIVE = {
    "漲停": 2.0, "大漲": 1.5, "飆": 1.5, "創新高": 1.5, "突破": 1.0, "強勢": 1.0,
    "利多": 1.5, "看好": 1.2, "買超": 1.0, "增產": 1.0, "接單": 1.0, "營收創新高": 2.0,
    "獲利": 0.8, "成長": 0.8, "續強": 1.0, "上修": 1.2, "題材": 0.6, "認養": 1.0,
    "外資買": 1.2, "投信買": 1.0, "報酬": 0.5, "填息": 1.0, "紅盤": 0.8,
}
_NEGATIVE = {
    "跌停": -2.0, "大跌": -1.5, "重挫": -1.5, "崩": -1.8, "創新低": -1.5, "跌破": -1.2,
    "利空": -1.5, "看壞": -1.2, "賣超": -1.0, "減產": -1.0, "砍單": -1.5, "衰退": -1.2,
    "虧損": -1.5, "下修": -1.5, "警示": -1.2, "處置": -1.5, "違約": -2.0, "掏空": -2.5,
    "外資賣": -1.2, "投信賣": -1.0, "貼息": -1.0, "套牢": -1.0, "追高": -0.8, "誘多": -1.5,
}


def news_score(titles: list[str]) -> tuple[int, float]:
    """Lexicon sentiment over recent headlines → (0-100 sub-score, raw_mean_polarity).

    raw_mean_polarity (roughly -2..+2) is returned too so the divergence check can tell
    'very hot' from 'mildly positive'. Neutral / no headlines → (50, 0.0)."""
    if not titles:
        return 50, 0.0
    total = 0.0
    hits = 0
    for t in titles:
        for term, w in _POSITIVE.items():
            if term in t:
                total += w
                hits += 1
        for term, w in _NEGATIVE.items():
            if term in t:
                total += w
                hits += 1
    if hits == 0:
        return 50, 0.0
    mean = total / hits
    # Map mean polarity (~-2..+2) to 0-100 around a neutral 50.
    score = 50 + mean * 18
    return int(min(max(round(score), 0), 100)), mean


def divergence_caveat(news_polarity: float, chip_score: int, fundamental_score: int) -> str | None:
    """Return an honest 追高風險 caveat when news is HOT but chip+fundamentals disagree.

    Hot news (mean polarity ≥ +0.8) while the smart-money/earnings picture is weak
    (chip < 45 or fundamental < 45) = the news-pumping-while-others-exit shape. We say
    'divergence / caution', never claim manipulation."""
    if news_polarity >= 0.8 and (chip_score < 45 or fundamental_score < 45):
        return (
            "新聞情緒偏熱，但籌碼/基本面未同步轉強（背離），"
            "留意是否為題材追高，非真實基本面驅動。"
        )
    if news_polarity <= -0.8 and chip_score >= 60:
        return "新聞情緒偏空，但籌碼仍偏多（背離），或為利空測底、法人逢低承接。"
    return None


def extract_titles(rows: list[dict[str, Any]], limit: int = 20) -> list[str]:
    """Pull the most recent headline strings from news_daily-shaped rows."""
    return [str(r.get("title") or "") for r in rows[:limit] if r.get("title")]
