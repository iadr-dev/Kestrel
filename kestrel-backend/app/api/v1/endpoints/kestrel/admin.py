"""Admin endpoints — job triggers, system status, data management. Admin-only access."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_session
from app.dependencies import get_current_user_id, is_admin_email
from app.schemas.admin import JobsStatusResponse, JobTriggerResponse

logger = get_logger(__name__)


def _tracked_task(job_name: str, fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Launch a background task with error logging (not silent fire-and-forget)."""
    async def _wrapper() -> None:
        try:
            await fn()
            logger.info("admin_job_completed", job=job_name)
        except Exception as e:
            logger.error("admin_job_failed", job=job_name, error=str(e)[:200])
    asyncio.create_task(_wrapper())


router = APIRouter(prefix="/admin", tags=["Admin"])


async def _require_admin(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_session)) -> str:
    """Dependency that ensures the current user is an admin."""
    from fastapi import HTTPException

    from app.models.user import User
    user = await db.get(User, user_id)
    if not user or not is_admin_email(user.email):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


class SetTierRequest(BaseModel):
    tier: str  # "free" | "premium" | "pro"


@router.post("/users/{target_user_id}/tier")
async def set_user_tier(
    target_user_id: str,
    request: SetTierRequest,
    _: str = Depends(_require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Placeholder subscription gateway — set a user's tier for local testing.

    A real payment provider (PayUni/TapPay/Stripe) will drive this via webhook later;
    for now it's an admin-only manual flip so all three tiers can be exercised end-to-end.
    """
    from fastapi import HTTPException

    from app.core.constants import UserTier
    from app.models.user import User

    valid = {t.value for t in UserTier}
    if request.tier not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid tier; must be one of {sorted(valid)}")

    user = await db.get(User, target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.tier = request.tier
    await db.commit()
    logger.info("admin_set_tier", target_user_id=target_user_id, tier=request.tier)
    return {"status": "ok", "user_id": target_user_id, "tier": request.tier}


@router.post("/jobs/daily-ingest", response_model=JobTriggerResponse)
async def trigger_daily_ingest(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger daily data ingest (prices + institutional + revenue)."""
    async def _run() -> None:
        from scripts.daily_ingest import daily_ingest
        await daily_ingest()
    _tracked_task("daily_ingest", _run)
    return {"status": "started", "job": "daily_ingest"}


@router.post("/jobs/daily-scoring", response_model=JobTriggerResponse)
async def trigger_daily_scoring(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger AI scoring computation."""
    async def _run() -> None:
        from scripts.daily_scoring import run_daily_scoring
        await run_daily_scoring(top_n=200)
    _tracked_task("job", _run)
    return {"status": "started", "job": "daily_scoring"}


@router.post("/jobs/weekly-themes", response_model=JobTriggerResponse)
async def trigger_weekly_themes(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger theme re-seed (FinMind base) + LLM discovery."""
    async def _run() -> None:
        from app.services.platform.theme_discovery import discover_themes
        from scripts.seed_themes import seed_all
        await seed_all()
        await discover_themes()
    _tracked_task("job", _run)
    return {"status": "started", "job": "weekly_themes"}


@router.post("/jobs/weekly-summaries", response_model=JobTriggerResponse)
async def trigger_weekly_summaries(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger AI summary generation for top stocks."""
    async def _run() -> None:
        from scripts.weekly_ai_summaries import generate_summaries
        await generate_summaries(max_stocks=50)
    _tracked_task("job", _run)
    return {"status": "started", "job": "weekly_summaries"}


@router.post("/jobs/extract-supply-chain", response_model=JobTriggerResponse)
async def trigger_supply_chain_extraction(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger supply chain relationship extraction."""
    async def _run() -> None:
        from scripts.extract_supply_chain import run_extraction
        await run_extraction(top_n=30)
    _tracked_task("job", _run)
    return {"status": "started", "job": "extract_supply_chain"}


@router.post("/jobs/scrape-profiles", response_model=JobTriggerResponse)
async def trigger_scrape_profiles(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger company profile scraping (TW + US)."""
    async def _run() -> None:
        from scripts.scrape_profiles import scrape_tw_profiles, scrape_us_profiles
        await scrape_tw_profiles()
        await scrape_us_profiles()
    _tracked_task("job", _run)
    return {"status": "started", "job": "scrape_profiles"}


@router.post("/jobs/alert-check", response_model=JobTriggerResponse)
async def trigger_alert_check(_: str = Depends(_require_admin)) -> dict[str, str]:
    """Manually trigger alert condition check."""
    asyncio.create_task(_run_alert_check())
    return {"status": "started", "job": "alert_check"}


async def _run_alert_check() -> None:
    try:
        from app.agent.alerts.scheduler import AlertScheduler
        from app.core.config import Settings
        from app.db.session import create_engine_and_session
        from app.providers.cache import InMemoryCache
        from app.providers.registry import ProviderRegistry
        from app.services.data.stock_service import StockService

        settings = Settings()
        stock_svc = StockService(registry=ProviderRegistry(), cache=InMemoryCache())
        alert_scheduler = AlertScheduler(stock_svc)
        session_factory = create_engine_and_session(settings)
        async with session_factory() as session:
            await alert_scheduler.check_alerts(session)
            await session.commit()
    except Exception:
        pass


@router.get("/jobs/status", response_model=JobsStatusResponse)
async def get_jobs_status(_: str = Depends(_require_admin)) -> dict[str, Any]:
    """Get scheduled jobs info."""
    from app.db.duckdb.engine import get_duckdb
    db = get_duckdb()

    # Get latest data dates. Async aquery_one so the admin endpoint doesn't block
    # the event loop on these 5 sequential scans.
    stats: dict[str, Any] = {}
    try:
        row = await db.aquery_one("SELECT MAX(date), COUNT(DISTINCT stock_id) FROM price_daily")
        assert row is not None
        stats["price_daily"] = {"latest_date": str(row[0]) if row[0] else None, "stocks": row[1]}
    except Exception:
        stats["price_daily"] = None

    try:
        row = await db.aquery_one("SELECT MAX(date), COUNT(DISTINCT stock_id) FROM institutional_daily")
        assert row is not None
        stats["institutional_daily"] = {"latest_date": str(row[0]) if row[0] else None, "stocks": row[1]}
    except Exception:
        stats["institutional_daily"] = None

    try:
        row = await db.aquery_one("SELECT MAX(date), COUNT(DISTINCT stock_id) FROM revenue_monthly")
        assert row is not None
        stats["revenue_monthly"] = {"latest_date": str(row[0]) if row[0] else None, "stocks": row[1]}
    except Exception:
        stats["revenue_monthly"] = None

    try:
        row = await db.aquery_one("SELECT COUNT(*), MAX(scored_at) FROM stock_scores")
        assert row is not None
        stats["stock_scores"] = {"count": row[0], "latest_date": str(row[1]) if row[1] else None}
    except Exception:
        stats["stock_scores"] = None

    try:
        row = await db.aquery_one("SELECT COUNT(*), MAX(generated_at) FROM ai_summaries")
        assert row is not None
        stats["ai_summaries"] = {"count": row[0], "latest_date": str(row[1]) if row[1] else None}
    except Exception:
        stats["ai_summaries"] = None

    return {
        "jobs": [
            {"id": "daily_ingest", "schedule": "Daily 19:00 TW", "description": "Prices + Institutional + Revenue"},
            {"id": "daily_scoring", "schedule": "Daily 19:30 TW", "description": "AI 4-factor scoring"},
            {"id": "alert_check", "schedule": "Every 30min (trading hours)", "description": "Price alert conditions"},
            {"id": "weekly_themes", "schedule": "Sunday 00:00 TW", "description": "Theme classification + discovery"},
            {"id": "weekly_summaries", "schedule": "Monday 02:00 TW", "description": "AI summary generation"},
            {"id": "weekly_supply_chain", "schedule": "Monday 04:00 TW", "description": "Supply chain relationship extraction"},
            {"id": "weekly_profiles", "schedule": "Monday 18:00 TW", "description": "Company profile scraping (TW + US)"},
        ],
        "data_status": stats,
    }
