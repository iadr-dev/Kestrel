"""Optional observability wiring: Sentry error tracking + Prometheus metrics.

Both are best-effort and dependency-optional (the `observability` extra). If the
package isn't installed or not configured, these are no-ops — the app runs fine
without them, so dev never needs the extra deps.
"""

from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry if a DSN is configured and the SDK is installed."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("sentry_dsn_set_but_sdk_missing", hint="uv sync --extra observability")
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=str(settings.environment),
        # Conservative trace sampling; tune per environment.
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("sentry_initialized", environment=str(settings.environment))


def setup_metrics(app: "FastAPI", settings: Settings) -> None:
    """Expose Prometheus metrics at /metrics if enabled and the lib is installed.

    Adds request count / latency / in-progress gauges per endpoint — the signals
    needed to watch p95 latency and error rate under load.
    """
    if not settings.metrics_enabled:
        return
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError:
        logger.info("metrics_enabled_but_lib_missing", hint="uv sync --extra observability")
        return
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/api/v1/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    logger.info("metrics_enabled", endpoint="/metrics")
