"""AI Analysis endpoints — stock scoring, rankings, and AI summaries."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import gate_rows, has_access, required_tier
from app.db.duckdb.engine import get_duckdb
from app.db.session import get_session
from app.dependencies import get_current_user_id_or_none, get_user_tier_and_keys
from app.schemas.ai_analysis import RankingsResponse, ScoreResponse, StockSummaryResponse
from app.services.platform.ai_scoring import compute_daily_scores

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    sort: str = Query("overall", description="Sort by: overall|technical|chip|fundamental|theme"),
    limit: int = Query(20, ge=1, le=100),
    user_id: str | None = Depends(get_current_user_id_or_none),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get AI-scored stock rankings. Uses pre-computed scores from DuckDB, falls back to on-the-fly.

    Tier-gated (AI feature): free/anonymous callers get the top rows + a locked strip;
    entitled tiers get the full ranking."""
    tier, _ = await get_user_tier_and_keys(session, user_id)
    db = get_duckdb()

    # Try pre-computed scores (widen window to find most recent available data)
    try:
        rows = await db.aquery("""
            SELECT stock_id, technical_score, chip_score, fundamental_score, theme_score, overall_score
            FROM stock_scores
            WHERE scored_at >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY scored_at DESC, overall_score DESC
            LIMIT ?
        """, [limit * 2])

        if rows:
            results = [
                {"stock_id": r[0], "technical_score": r[1], "chip_score": r[2],
                 "fundamental_score": r[3], "theme_score": r[4], "overall_score": r[5]}
                for r in rows
            ]
        else:
            results = await compute_daily_scores(top_n=limit * 2)
    except Exception:
        results = await compute_daily_scores(top_n=limit * 2)

    sort_key = f"{sort}_score" if sort != "overall" else "overall_score"
    results.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    top = results[:limit]
    gated = gate_rows(top, tier, feature="ai_score")
    return {
        "data": gated["rows"],
        "count": len(gated["rows"]),
        "sort": sort,
        "locked": gated["locked"],
        "total": gated["total"],
        "required_tier": gated["required_tier"],
    }


@router.get("/summary/{stock_id}", response_model=StockSummaryResponse)
async def get_stock_summary(
    stock_id: str,
    at: str | None = Query(None),
    user_id: str | None = Depends(get_current_user_id_or_none),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get an AI analysis summary for ANY asset (TW/US · stock/ETF).

    Resolve-or-generate: returns the stored summary if present; otherwise TW stocks are
    generated on-demand via the LLM summariser (cached), while US/ETF get a concise
    data-backed summary synthesised from the resolved score. `at` = asset-kind hint.

    Tier-gated: AI summary is a premium feature. Free/anonymous callers get a locked
    envelope (no data) rather than a 401, so the frontend can render a teaser."""
    tier, _ = await get_user_tier_and_keys(db, user_id)
    if not has_access("ai_summary", tier):
        return {"data": None, "locked": True, "required_tier": required_tier("ai_summary")}

    from app.services.platform.scoring.resolver import resolve_summary
    result = await resolve_summary(stock_id, at)
    if not result:
        return {"data": None, "message": "No AI summary available for this stock yet."}
    return {"data": result}


@router.get("/score/{stock_id}", response_model=ScoreResponse)
async def get_stock_score(
    stock_id: str,
    at: str | None = Query(None),
    user_id: str | None = Depends(get_current_user_id_or_none),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get an individual score for ANY asset (TW/US · stock/ETF), across dimensions.

    Delegates to the market-aware resolver: it returns a fresh stored row if present,
    otherwise computes on-demand (TW via the DuckDB batch; US/ETF via yfinance/cmoney +
    the per-kind factor model), persists it, and returns it. `at` optionally passes the
    asset kind hint (e.g. 'us-etf') the id alone can't disambiguate.

    Tier-gated: full score breakdown is premium. Free/anonymous callers get a locked
    teaser envelope carrying ONLY the overall score band (no factor breakdown)."""
    tier, _ = await get_user_tier_and_keys(db, user_id)
    from app.services.platform.scoring.resolver import resolve_score
    result = await resolve_score(stock_id, at)
    if not result:
        return {"data": None, "message": "No score data available for this stock."}

    if not has_access("ai_score", tier):
        # Teaser: keep only the overall score (headline band), withhold the breakdown.
        teaser = {"stock_id": result.get("stock_id"), "overall": result.get("overall_score")}
        return {"data": teaser, "locked": True, "required_tier": required_tier("ai_score")}
    return {"data": result}
