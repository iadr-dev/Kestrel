from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_current_user_id, get_provider_registry
from app.providers.registry import ProviderRegistry
from app.schemas.health import DBHealthResponse, HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> dict[str, str]:
    """Liveness probe — process is up. Cheap, no dependencies touched."""
    return {"status": "healthy"}


async def _check_dependencies(request: Request) -> dict[str, object]:
    """Check DuckDB, SQLAlchemy, and the cache backend. Used by /db and /ready."""
    result: dict[str, object] = {}

    # DuckDB — async so we don't block the loop.
    try:
        from app.db.duckdb.engine import get_duckdb
        db = get_duckdb()
        row = await db.aquery_one("SELECT COUNT(DISTINCT stock_id) FROM price_daily")
        result["duckdb"] = {"status": "ok", "stocks": row[0] if row else 0}
    except Exception as e:
        result["duckdb"] = {"status": "error", "error": str(e)[:100]}

    # SQLAlchemy — actually execute SELECT 1 (the old check was a no-op).
    try:
        from sqlalchemy import text

        from app.db.session import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        result["sqlalchemy"] = {"status": "ok"}
    except Exception as e:
        result["sqlalchemy"] = {"status": "error", "error": str(e)[:100]}

    # Cache backend (Redis or in-memory) — round-trip a probe key.
    try:
        cache = getattr(request.app.state, "cache", None)
        backend = type(cache).__name__ if cache else "none"
        if cache is not None:
            await cache.set("health:probe", 1, ttl=10)
            ok = await cache.get("health:probe")
            result["cache"] = {"status": "ok" if ok == 1 else "degraded", "backend": backend}
        else:
            result["cache"] = {"status": "error", "backend": backend}
    except Exception as e:
        result["cache"] = {"status": "error", "error": str(e)[:100]}

    return result


@router.get("/db", response_model=DBHealthResponse)
async def db_health(request: Request) -> dict[str, object]:
    """Check DuckDB + SQLAlchemy + cache connectivity (detailed)."""
    return await _check_dependencies(request)


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe for k8s — 200 only if all critical deps are healthy.

    Returns 503 when any dependency reports an error so the orchestrator stops
    routing traffic to a broken pod.
    """
    checks = await _check_dependencies(request)
    healthy = all(
        isinstance(v, dict) and v.get("status") in ("ok", "degraded")
        for v in checks.values()
    )
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "not_ready", "checks": checks},
    )


@router.get("/providers")
async def provider_health(
    registry: ProviderRegistry = Depends(get_provider_registry),
    _: str = Depends(get_current_user_id),
) -> dict[str, object]:
    """Provider health (requires auth — exposes rate limit metrics)."""
    return await registry.health_check_all()
