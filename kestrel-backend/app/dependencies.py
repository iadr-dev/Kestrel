"""FastAPI dependency injection — wires providers, cache, and services."""

from functools import lru_cache
from typing import TYPE_CHECKING, cast

from fastapi import Depends, Request

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.duckdb.market_cache import MarketDataCache
    from app.services.platform.media_service import MediaService

from app.core.config import Settings
from app.core.security import decode_token
from app.providers.cache import CacheBackend
from app.providers.registry import ProviderRegistry
from app.services.data.derivative_service import DerivativeService
from app.services.data.etf_service import ETFService
from app.services.data.fundamental_service import FundamentalService
from app.services.data.institutional_service import InstitutionalService
from app.services.data.international_service import InternationalService
from app.services.data.macro_service import MacroService
from app.services.data.market_service import MarketService
from app.services.data.screener_service import ScreenerService
from app.services.data.stock_service import StockService
from app.services.platform.auth_service import AuthService


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def get_current_user_id(request: Request) -> str:
    """Extract user_id from Bearer token. Raises 401 if not authenticated."""
    from fastapi import HTTPException

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    settings = get_settings()
    payload = decode_token(token, settings)
    if payload and payload.get("type") == "access":
        user_id = payload.get("sub")
        if user_id:
            return cast(str, user_id)
    raise HTTPException(status_code=401, detail="Invalid or expired token")


def is_admin_email(email: str | None) -> bool:
    """Check if email belongs to an admin. Single source of truth via config."""
    if not email:
        return False
    settings = get_settings()
    return email in settings.admin_emails


def is_admin_line_id(line_id: str | None) -> bool:
    """Check if LINE ID belongs to an admin."""
    if not line_id:
        return False
    settings = get_settings()
    return line_id == settings.admin_line_id


async def get_current_user_id_or_none(request: Request) -> str | None:
    """Extract user_id if token present, return None if not. For public endpoints that behave differently when authed."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not token:
        return None
    settings = get_settings()
    payload = decode_token(token, settings)
    if payload and payload.get("type") == "access":
        return payload.get("sub")
    return None




async def get_user_tier_and_keys(db: "AsyncSession", user_id: str | None) -> tuple[str, bool]:
    """Resolve (tier, has_user_keys) for a user.

    Single place the BYOK signal is computed: a user is "BYOK" if they have any stored
    `custom_api_keys` semantic fact. Anonymous callers are treated as free / no-keys.
    Never raises — returns ("free", False) on any failure so gating degrades safely.
    """
    if not user_id:
        return "free", False
    tier = "free"
    try:
        from app.models.user import User
        user = await db.get(User, user_id)
        if user:
            tier = user.tier
    except Exception:
        pass
    has_keys = False
    try:
        from app.agent.memory.semantic import SemanticMemory
        facts = await SemanticMemory(db, user_id).get_facts_by_type("custom_api_keys")
        has_keys = any(f.fact_value for f in facts)
    except Exception:
        pass
    return tier, has_keys


def require_feature(feature_key: str):  # type: ignore[no-untyped-def]
    """Dependency factory: 403 if the caller's tier can't access `feature_key`.

    Use for HARD gates (deep_research, main_force) where there's no teaser — the
    endpoint must not run at all for an unentitled user.
    """
    from app.db.session import get_session

    async def _dep(
        request: Request,
        db: "AsyncSession" = Depends(get_session),
    ) -> None:
        from app.agent.hooks.tier_gate import TierGate
        user_id = await get_current_user_id_or_none(request)
        tier, _ = await get_user_tier_and_keys(db, user_id)
        TierGate().check_feature(feature_key, tier)

    return _dep


async def get_provider_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


async def get_cache(request: Request) -> CacheBackend:
    return cast(CacheBackend, request.app.state.cache)


async def get_market_cache(request: Request) -> "MarketDataCache | None":
    return getattr(request.app.state, "market_cache", None)


async def get_stock_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> StockService:
    return StockService(registry=registry, cache=cache, market_cache=market_cache)


async def get_market_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> MarketService:
    return MarketService(registry=registry, cache=cache)


async def get_etf_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> ETFService:
    return ETFService(registry=registry, cache=cache, market_cache=market_cache)


async def get_institutional_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> InstitutionalService:
    return InstitutionalService(registry=registry, cache=cache)


async def get_fundamental_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> FundamentalService:
    return FundamentalService(registry=registry, cache=cache)


async def get_derivative_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> DerivativeService:
    return DerivativeService(registry=registry, cache=cache)


async def get_international_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> InternationalService:
    return InternationalService(registry=registry, cache=cache)


async def get_macro_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
) -> MacroService:
    return MacroService(registry=registry, cache=cache)


async def get_screener_service(
    registry: ProviderRegistry = Depends(get_provider_registry),
    cache: CacheBackend = Depends(get_cache),
    market_cache: "MarketDataCache | None" = Depends(get_market_cache),
) -> ScreenerService:
    return ScreenerService(registry=registry, cache=cache, market_cache=market_cache)


async def get_auth_service(request: Request) -> AuthService:
    return cast(AuthService, request.app.state.auth_service)


async def get_media_service() -> "MediaService":
    """STT/TTS service. Stateless (holds Settings only), constructed per request."""
    from app.services.platform.media_service import MediaService
    return MediaService(get_settings())
