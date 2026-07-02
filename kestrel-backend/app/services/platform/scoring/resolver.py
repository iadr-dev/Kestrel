"""Score resolver — the single entry point for "give me a score for any id".

Flow (cache-first + on-demand, per the established service pattern):
  1. Fresh row in stock_scores?  → return it.
  2. Miss/stale → compute market-aware:
       - TW stock: reuse the DuckDB batch path (compute_daily_scores) — the chip/theme
         factors need the ingested tables.
       - US stock / TW-ETF / US-ETF: fetch from yfinance/cmoney, reshape via adapters,
         run the pure compute_* functions + the per-kind factor weights (models.blend).
  3. Persist the computed row (with `kind`) back to stock_scores + return.

Returns a uniform dict the endpoint/frontend consume regardless of kind:
  {stock_id, kind, overall_score, technical_score, chip_score, fundamental_score,
   theme_score, sub_scores{...}, caveats[...], scored_at}
"""

from datetime import date
from typing import Any

from app.core.logging import get_logger
from app.services.platform import ai_scoring
from app.services.platform.scoring import adapters, models, news_sentiment

logger = get_logger(__name__)

# Freshness: a stored score older than this many days triggers a recompute.
_STALE_DAYS = 1


async def resolve_score(stock_id: str, hint: str | None = None) -> dict[str, Any] | None:
    """Resolve (table-hit or compute-and-persist) the AI score for any id/kind."""
    kind = models.detect_kind(stock_id, hint)

    # 1. Fresh stored row of the SAME kind? (The volume-ranked batch tags everything
    # 'tw-stock', including ETFs like 0050 — so an ETF must not be served that stock-
    # shaped row; a kind mismatch forces the correct ETF/US recompute below.)
    stored = await _read_stored(stock_id)
    if stored is not None and stored.get("kind") == kind:
        return stored

    # 2. Compute on-demand, market-aware.
    try:
        if kind == "tw-stock":
            result = await _score_tw_stock(stock_id)
        elif kind == "tw-etf" or kind == "us-etf":
            result = await _score_etf(stock_id, kind)
        else:  # us-stock
            result = await _score_us_stock(stock_id)
    except Exception as e:
        logger.warning("resolve_score_failed", stock_id=stock_id, kind=kind, error=str(e)[:120])
        return None

    if result is None:
        return None

    # 3. Persist (best-effort) + return.
    await _persist(result)
    return result


async def resolve_summary(stock_id: str, hint: str | None = None) -> dict[str, Any] | None:
    """Resolve (stored-or-generate) an AI summary for any id/kind.

    1. Stored row in ai_summaries → return.
    2. TW stock → reuse the LLM generator (generate_summaries) for this one id, cache 7d.
    3. US / ETF → synthesize a concise summary from the resolved score's sub-scores +
       caveats (no heavy per-kind LLM path yet — honest, data-backed, and cheap)."""
    stored = await _read_stored_summary(stock_id)
    if stored is not None:
        return stored

    kind = models.detect_kind(stock_id, hint)
    if kind == "tw-stock":
        try:
            from scripts.weekly_ai_summaries import generate_summaries
            await generate_summaries(stock_ids=[stock_id])
        except Exception as e:
            logger.warning("summary_generate_failed", stock_id=stock_id, error=str(e)[:120])
        return await _read_stored_summary(stock_id)

    if kind == "us-stock":
        # US stocks get a full LLM narrative too (fundamentals/analyst/trend), parity
        # with TW. Falls back to the score-synthesized summary if generation fails.
        try:
            from app.services.platform.scoring.us_summary import generate_us_summary
            result = await generate_us_summary(stock_id)
            if result:
                return result
        except Exception as e:
            logger.warning("us_summary_failed", stock_id=stock_id, error=str(e)[:120])

    # ETFs (and US-stock fallback): synthesize from the resolved score (sub-scores +
    # caveats) — the industry-standard "scorecard" approach for ETFs (Morningstar/ETF.com).
    score = await resolve_score(stock_id, hint)
    if not score:
        return None
    return _summary_from_score(score)


async def _read_stored_summary(stock_id: str) -> dict[str, Any] | None:
    import json

    from app.db.duckdb.engine import get_duckdb
    try:
        row = await get_duckdb().aquery_one(
            "SELECT stock_id, position_label, summary, factors, swot, generated_at "
            "FROM ai_summaries WHERE stock_id = ?", [stock_id]
        )
    except Exception:
        return None
    if not row:
        return None
    return {
        "stock_id": row[0], "position_label": row[1], "summary": row[2],
        "factors": json.loads(row[3]) if row[3] else [],
        "swot": json.loads(row[4]) if row[4] else {},
        "generated_at": str(row[5]) if row[5] else None,
    }


def _summary_from_score(score: dict[str, Any]) -> dict[str, Any]:
    """Compose a concise, data-backed summary for US/ETF from the resolved score —
    position label from the overall, factors from the sub-scores, caveats included."""
    overall = score.get("overall_score", 50)
    label = "偏多" if overall >= 65 else "偏空" if overall <= 40 else "中性"
    sub = score.get("sub_scores", {}) or {}
    factors = [
        {"category": k, "polarity": "positive" if v >= 60 else "negative" if v <= 40 else "neutral",
         "text": f"{k}: {v}"}
        for k, v in sub.items()
    ]
    caveats = score.get("caveats", [])
    summary = f"綜合評分 {overall}/100（{label}）。" + ("；".join(caveats) if caveats else "")
    return {
        "stock_id": score["stock_id"], "position_label": label, "summary": summary,
        "factors": factors, "swot": {}, "generated_at": score.get("scored_at"),
    }


async def _read_stored(stock_id: str) -> dict[str, Any] | None:
    from app.db.duckdb.engine import get_duckdb
    try:
        row = await get_duckdb().aquery_one(
            "SELECT stock_id, technical_score, chip_score, fundamental_score, theme_score, "
            "overall_score, kind, scored_at FROM stock_scores WHERE stock_id = ? "
            "ORDER BY scored_at DESC LIMIT 1",
            [stock_id],
        )
    except Exception:
        return None
    if not row:
        return None
    scored_at = str(row[7]) if row[7] else ""
    if scored_at and scored_at[:10] < str(date.today() - _td(_STALE_DAYS)):
        return None  # stale → force recompute
    return {
        "stock_id": row[0], "kind": row[6] or "tw-stock",
        "technical_score": row[1], "chip_score": row[2],
        "fundamental_score": row[3], "theme_score": row[4],
        "overall_score": row[5], "scored_at": scored_at, "caveats": [], "sub_scores": {},
    }


def _td(days: int) -> "Any":
    from datetime import timedelta
    return timedelta(days=days)


async def _score_tw_stock(stock_id: str) -> dict[str, Any] | None:
    """TW stock: reuse the DuckDB batch (chip/theme need ingested tables), then overlay
    the news-sentiment factor + divergence caveat + S/R technical caveat."""
    results = await ai_scoring.compute_daily_scores(top_n=500)
    match = next((r for r in results if r["stock_id"] == stock_id), None)
    if not match:
        return None

    caveats: list[str] = []
    # News sentiment overlay + divergence.
    titles = await _recent_news_titles(stock_id)
    news_sub, polarity = news_sentiment.news_score(titles)
    div = news_sentiment.divergence_caveat(polarity, match.get("chip_score", 50), match.get("fundamental_score", 50))
    if div:
        caveats.append(div)

    # Re-blend to include the small news weight (models has 'news' for tw-stock).
    sub = {
        "technical": match.get("technical_score", 50),
        "chip": match.get("chip_score", 50),
        "theme": match.get("theme_score", 50),
        "fundamental": match.get("fundamental_score", 50),
        "news": news_sub,
    }
    overall = models.blend(sub, "tw-stock")

    # S/R reversal caveat from the stock's recent OHLCV.
    prices = await _recent_prices_tw(stock_id)
    sr = ai_scoring.technical_caveat(prices)
    if sr:
        caveats.append(sr)

    return {
        "stock_id": stock_id, "kind": "tw-stock",
        "technical_score": sub["technical"], "chip_score": sub["chip"],
        "fundamental_score": sub["fundamental"], "theme_score": sub["theme"],
        "overall_score": overall, "scored_at": str(date.today()),
        "sub_scores": {**sub}, "caveats": caveats,
    }


async def _score_us_stock(stock_id: str) -> dict[str, Any] | None:
    """US stock: yfinance history + info → technical + fundamental + analyst."""
    from app.providers.yfinance import YFinanceProvider
    yf = YFinanceProvider()
    hist = await yf.get_history(stock_id, period="6mo", interval="1d")
    info = await yf.get_info(stock_id)
    prices = adapters.normalize_yf_history(hist)
    if len(prices) < 20 and not info:
        return None

    tech = ai_scoring.compute_technical_score(prices) if len(prices) >= 20 else 50
    fund = adapters.us_fundamental_score(info)
    # Inject current price so analyst upside is computed vs. the latest close.
    if prices:
        info = {**info, "_current": prices[-1]["close"]}
    analyst = adapters.us_analyst_score(info)

    sub = {"technical": tech, "fundamental": fund, "analyst": analyst}
    overall = models.blend(sub, "us-stock")
    caveats: list[str] = []
    sr = ai_scoring.technical_caveat(prices)
    if sr:
        caveats.append(sr)

    return {
        "stock_id": stock_id, "kind": "us-stock",
        "technical_score": tech, "chip_score": None,
        "fundamental_score": fund, "theme_score": None,
        "overall_score": overall, "scored_at": str(date.today()),
        "sub_scores": {**sub, "analyst": analyst}, "caveats": caveats,
    }


async def _score_etf(stock_id: str, kind: models.AssetKind) -> dict[str, Any] | None:
    """ETF (TW or US): yield/premium + expense + technical, or expense_yield + risk +
    technical for US. Uses the /etf/profile-style data (cmoney + NAV) for TW, yfinance
    for US."""
    from app.providers.yfinance import YFinanceProvider
    yf = YFinanceProvider()
    hist = await yf.get_history(stock_id, period="6mo", interval="1d")
    prices = adapters.normalize_yf_history(hist)
    tech = ai_scoring.compute_technical_score(prices) if len(prices) >= 20 else 50

    profile: dict[str, Any] = {}
    info: dict[str, Any] = {}
    if kind == "tw-etf":
        try:
            from app.scrapers.cmoney_etf import scrape_cmoney_etf
            profile = await scrape_cmoney_etf(stock_id) or {}
        except Exception:
            profile = {}
        sub = {
            "yield_premium": adapters.etf_yield_premium_score(profile),
            "expense": adapters.etf_expense_score(profile),
            "technical": tech,
        }
    else:  # us-etf
        info = await yf.get_info(stock_id)
        profile = {
            "yield_pct": (info.get("dividend_yield") or 0) * 100 if info.get("dividend_yield") else None,
            "expense_ratio_pct": None,  # yfinance funds-data expense not always present
        }
        sub = {
            "expense_yield": adapters.etf_expense_yield_score(profile),
            "risk": adapters.etf_risk_score(info),
            "technical": tech,
        }

    overall = models.blend(sub, kind)
    return {
        "stock_id": stock_id, "kind": kind,
        "technical_score": tech, "chip_score": None,
        "fundamental_score": None, "theme_score": None,
        "overall_score": overall, "scored_at": str(date.today()),
        "sub_scores": sub, "caveats": [],
    }


async def _persist(result: dict[str, Any]) -> None:
    """Write the computed row into stock_scores (best-effort; never raises)."""
    from app.db.duckdb.engine import get_duckdb
    try:
        db = get_duckdb()

        def _w() -> None:
            with db.write_connection() as conn:
                # Ensure the table + kind column exist (this resolver may run before the
                # daily batch on a fresh DB — e.g. a US stock viewed first).
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_scores (
                        stock_id VARCHAR NOT NULL,
                        technical_score INTEGER, chip_score INTEGER,
                        fundamental_score INTEGER, theme_score INTEGER,
                        overall_score INTEGER, kind VARCHAR DEFAULT 'tw-stock',
                        scored_at DATE DEFAULT CURRENT_DATE, PRIMARY KEY (stock_id)
                    )
                """)
                conn.execute("ALTER TABLE stock_scores ADD COLUMN IF NOT EXISTS kind VARCHAR DEFAULT 'tw-stock'")
                conn.execute(
                    "INSERT OR REPLACE INTO stock_scores "
                    "(stock_id, technical_score, chip_score, fundamental_score, theme_score, "
                    "overall_score, kind, scored_at) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_DATE)",
                    [
                        result["stock_id"], result.get("technical_score"), result.get("chip_score"),
                        result.get("fundamental_score"), result.get("theme_score"),
                        result.get("overall_score"), result.get("kind"),
                    ],
                )
        import asyncio
        await asyncio.to_thread(_w)
    except Exception as e:
        logger.warning("score_persist_failed", stock_id=result.get("stock_id"), error=str(e)[:100])


async def _recent_news_titles(stock_id: str) -> list[str]:
    from app.db.duckdb.engine import get_duckdb
    try:
        rows = await get_duckdb().aquery(
            "SELECT title FROM news_daily WHERE stock_id = ? ORDER BY ts DESC LIMIT 20", [stock_id]
        )
        return [r[0] for r in rows if r and r[0]]
    except Exception:
        return []


async def _recent_prices_tw(stock_id: str) -> list[dict[str, Any]]:
    from app.db.duckdb.engine import get_duckdb
    try:
        rows = await get_duckdb().aquery(
            "SELECT open, high, low, close, volume FROM price_daily WHERE stock_id = ? "
            "ORDER BY date DESC LIMIT 40", [stock_id]
        )
        # reverse to chronological
        return [
            {"open": r[0], "high": r[1], "low": r[2], "close": r[3], "volume": r[4]}
            for r in reversed(rows)
        ]
    except Exception:
        return []
