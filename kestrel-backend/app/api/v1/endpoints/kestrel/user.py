from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import entitlements_for
from app.db.session import get_session
from app.dependencies import get_current_user_id, get_user_tier_and_keys
from app.schemas.common import StatusResponse
from app.schemas.user import (
    AgentSettingsResponse,
    PortfolioCreateResponse,
    PortfolioListResponse,
    ProfileUpdateResponse,
    UIPreferencesResponse,
    UserProfileResponse,
    WatchlistCreateResponse,
    WatchlistItemAddResponse,
    WatchlistItemDeleteResponse,
    WatchlistListResponse,
)
from app.services.platform.user_service import UserService

router = APIRouter(prefix="/user", tags=["User"])


async def _chats_used_today(db: AsyncSession, user_id: str) -> int:
    """Count today's AI chats for the user (same source as the tier gate)."""
    try:
        from datetime import date as date_cls

        from sqlalchemy import func, select

        from app.agent.observe import LLMTrace
        stmt = select(func.count()).select_from(LLMTrace).where(
            LLMTrace.user_id == user_id,
            LLMTrace.created_at >= str(date_cls.today()),
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)
    except Exception:
        return 0


async def _build_entitlements(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Server-computed entitlements payload for a user (the client's single source)."""
    tier, has_keys = await get_user_tier_and_keys(db, user_id)
    used = await _chats_used_today(db, user_id)
    return entitlements_for(tier, has_user_keys=has_keys, chat_used=used)


class CreatePortfolioRequest(BaseModel):
    name: str
    holdings: list[dict[str, Any]] = []


class CreateWatchlistRequest(BaseModel):
    name: str
    market: str = "TW"
    items: list[dict[str, Any]] = []


async def _get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)


@router.get("/portfolio", response_model=PortfolioListResponse)
async def get_portfolios(
    service: UserService = Depends(_get_user_service),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    data = await service.get_portfolios(user_id=user_id)
    return {"data": data, "count": len(data)}


@router.post("/portfolio", response_model=PortfolioCreateResponse)
async def create_portfolio(
    request: CreatePortfolioRequest,
    service: UserService = Depends(_get_user_service),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    portfolio = await service.create_portfolio(
        user_id=user_id, name=request.name, holdings=request.holdings
    )
    return {"data": portfolio}


DEFAULT_WATCHLISTS: list[dict[str, Any]] = [
    {
        "name": "半導體",
        "market": "TW",
        "items": [
            {"stock_id": "2330"},  # 台積電
            {"stock_id": "2454"},  # 聯發科
            {"stock_id": "3711"},  # 日月光
            {"stock_id": "2303"},  # 聯電
        ],
    },
    {
        "name": "權值股",
        "market": "TW",
        "items": [
            {"stock_id": "2317"},  # 鴻海
            {"stock_id": "2382"},  # 廣達
            {"stock_id": "2881"},  # 富邦金
            {"stock_id": "2882"},  # 國泰金
            {"stock_id": "2412"},  # 中華電
        ],
    },
    {
        "name": "US Tech",
        "market": "US",
        "items": [
            {"stock_id": "NVDA"},
            {"stock_id": "AAPL"},
            {"stock_id": "TSLA"},
            {"stock_id": "MSFT"},
        ],
    },
    {
        "name": "US Index",
        "market": "US",
        "items": [
            {"stock_id": "SPY"},
            {"stock_id": "QQQ"},
            {"stock_id": "DIA"},
        ],
    },
    {
        "name": "台股 ETF",
        "market": "ETF",
        "items": [
            {"stock_id": "0050"},  # 元大台灣50
            {"stock_id": "0056"},  # 元大高股息
            {"stock_id": "00878"},  # 國泰永續高股息
            {"stock_id": "00919"},  # 群益台灣精選高息
        ],
    },
    {
        "name": "債券/海外 ETF",
        "market": "ETF",
        "items": [
            {"stock_id": "00679B"},  # 元大美債20年
            {"stock_id": "00713"},  # 元大台灣高息低波
            {"stock_id": "00757"},  # 統一FANG+
        ],
    },
]


@router.get("/watchlist", response_model=WatchlistListResponse)
async def get_watchlists(
    market: str | None = None,
    service: UserService = Depends(_get_user_service),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    data = await service.get_watchlists(user_id=user_id, market=market)
    # Seed default watchlists if empty
    if not data:
        for wl in DEFAULT_WATCHLISTS:
            if market and wl["market"] != market:
                continue
            await service.create_watchlist(
                user_id=user_id, name=wl["name"], items=wl["items"], market=wl["market"]
            )
        data = await service.get_watchlists(user_id=user_id, market=market)
    return {"data": data, "count": len(data)}


@router.post("/watchlist", response_model=WatchlistCreateResponse)
async def create_watchlist(
    request: CreateWatchlistRequest,
    service: UserService = Depends(_get_user_service),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    watchlist = await service.create_watchlist(
        user_id=user_id, name=request.name, items=request.items, market=request.market
    )
    return {"data": watchlist}


class AddWatchlistItemRequest(BaseModel):
    stock_id: str
    watchlist_id: str | None = None


@router.post("/watchlist/item", response_model=WatchlistItemAddResponse)
async def add_watchlist_item(
    request: AddWatchlistItemRequest,
    service: UserService = Depends(_get_user_service),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Add a stock to the user's first watchlist (creates one if none exist)."""
    from app.db.repositories.watchlist_repo import WatchlistRepository
    repo = WatchlistRepository(db)
    watchlists = await repo.get_by_user(user_id)

    if request.watchlist_id:
        target_id = request.watchlist_id
    elif watchlists:
        target_id = watchlists[0].id
    else:
        wl = await repo.create_with_items(user_id=user_id, name="My Watchlist", items=[])
        target_id = wl.id

    item = await repo.add_item(target_id, request.stock_id)
    return {"status": "added", "item": {"id": item.id, "stock_id": item.stock_id}}


@router.delete("/watchlist/item/{stock_id}", response_model=WatchlistItemDeleteResponse)
async def remove_watchlist_item(
    stock_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Remove a stock from all of the user's watchlists."""
    from sqlalchemy import delete, select

    from app.models.watchlist import Watchlist, WatchlistItem

    stmt = (
        select(WatchlistItem.id)
        .join(Watchlist, WatchlistItem.watchlist_id == Watchlist.id)
        .where(Watchlist.user_id == user_id, WatchlistItem.stock_id == stock_id)
    )
    result = await db.execute(stmt)
    item_ids = [row[0] for row in result.all()]

    if item_ids:
        await db.execute(delete(WatchlistItem).where(WatchlistItem.id.in_(item_ids)))
        await db.flush()

    return {"status": "removed", "stock_id": stock_id}


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    custom_api_keys: dict[str, str] | None = None


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get current user profile from database."""
    from app.db.repositories.user_repo import UserRepository
    repo = UserRepository(db)
    user = await repo.get_with_full_profile(user_id)

    # Load stored API keys from semantic memory (show which keys are set, not values)
    api_keys_set: dict[str, str] = {}
    try:
        from app.agent.memory.semantic import SemanticMemory
        memory = SemanticMemory(db, user_id)
        facts = await memory.get_facts_by_type("custom_api_keys")
        for fact in facts:
            if fact.fact_value:
                api_keys_set[fact.fact_key] = fact.fact_value
    except Exception:
        pass

    entitlements = await _build_entitlements(db, user_id)
    if not user:
        return {
            "id": user_id,
            "display_name": "User",
            "email": None,
            "tier": "free",
            "picture_url": None,
            "custom_api_keys": api_keys_set,
            "entitlements": entitlements,
        }
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "picture_url": user.picture_url,
        "tier": user.tier,
        "custom_api_keys": api_keys_set,
        "entitlements": entitlements,
    }


@router.get("/entitlements")
async def get_entitlements(
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Standalone entitlements payload (cheap client poll after tier/BYOK changes)."""
    return await _build_entitlements(db, user_id)


@router.put("/profile", response_model=ProfileUpdateResponse)
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Update user profile and API keys."""
    from app.db.repositories.user_repo import UserRepository
    repo = UserRepository(db)
    user = await repo.get_with_full_profile(user_id)
    if user:
        if request.display_name:
            user.display_name = request.display_name

    # Store custom API keys in semantic memory (persisted, per-user)
    if request.custom_api_keys:
        from app.agent.memory.semantic import SemanticMemory
        memory = SemanticMemory(db, user_id)
        for key_name, key_value in request.custom_api_keys.items():
            if key_value:
                await memory.learn_fact("custom_api_keys", key_name, key_value, confidence=1.0, is_user_set=True)

    return {
        "status": "updated",
        "display_name": request.display_name,
        "custom_api_keys_set": list((request.custom_api_keys or {}).keys()),
    }


# Allow-list of deletable custom API key names (mirrors the keys the agent reads).
_DELETABLE_API_KEYS = {"anthropic_api_key", "openai_api_key", "gemini_api_key", "openrouter_api_key"}


@router.delete("/api-keys/{key_name}", response_model=StatusResponse)
async def delete_api_key(
    key_name: str,
    db: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    """Remove a stored custom API key so the user falls back to the platform key."""
    if key_name not in _DELETABLE_API_KEYS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown API key: {key_name}")
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id)
    removed = await memory.forget_fact_by_key("custom_api_keys", key_name)
    return {"status": "deleted" if removed else "not_found"}


# === Agent Settings ===

class AgentSettingsRequest(BaseModel):
    response_style: str | None = None  # "professional" | "casual" | "concise" | "detailed" | "analyst"
    custom_instructions: str | None = None
    focus_areas: list[str] | None = None  # ["technical", "fundamental", "news", "institutional", "macro"]
    market_preference: str | None = None  # "tw" | "us" | "etf"


@router.get("/agent-settings", response_model=AgentSettingsResponse)
async def get_agent_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get user's agent personalization settings."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id)
    facts = await memory.get_facts_by_type("agent_settings")
    settings: dict[str, Any] = {
        "response_style": "professional",
        "custom_instructions": "",
        "focus_areas": ["technical", "fundamental"],
    }
    for fact in facts:
        if fact.fact_key == "response_style":
            settings["response_style"] = fact.fact_value
        elif fact.fact_key == "custom_instructions":
            settings["custom_instructions"] = fact.fact_value
        elif fact.fact_key == "focus_areas":
            # Stored as comma-joined; an empty string must round-trip to [] (not [""]).
            settings["focus_areas"] = [a for a in fact.fact_value.split(",") if a]
    return {"data": settings}


@router.put("/agent-settings", response_model=StatusResponse)
async def update_agent_settings(
    request: AgentSettingsRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Update user's agent personalization settings."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id)
    if request.response_style:
        await memory.learn_fact("agent_settings", "response_style", request.response_style, confidence=1.0, is_user_set=True)
    if request.custom_instructions is not None:
        await memory.learn_fact("agent_settings", "custom_instructions", request.custom_instructions, confidence=1.0, is_user_set=True)
    if request.focus_areas is not None:
        await memory.learn_fact("agent_settings", "focus_areas", ",".join(request.focus_areas), confidence=1.0, is_user_set=True)
    # market_preference is owned by ui_preferences (/user/preferences), not here.
    return {"status": "updated"}


# === UI Preferences (theme, language, market — synced across devices) ===

class UIPreferencesRequest(BaseModel):
    theme: str | None = None  # "dark" | "light" | "system"
    language: str | None = None  # "zh-TW" | "en"
    market_preference: str | None = None  # "tw" | "us" | "etf"


@router.get("/preferences", response_model=UIPreferencesResponse)
async def get_ui_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get user's UI preferences (synced across all devices)."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id)
    facts = await memory.get_facts_by_type("ui_preferences")
    # Default theme is "dark" to match the app's defaultTheme (Providers.tsx). A
    # "system" default would flip the UI to light on an OS-light machine the first
    # time the settings page hydrates these prefs.
    prefs: dict[str, str] = {
        "theme": "dark",
        "language": "zh-TW",
        "market_preference": "tw",
    }
    for fact in facts:
        if fact.fact_key in prefs:
            prefs[fact.fact_key] = fact.fact_value
    return {"data": prefs}


@router.put("/preferences", response_model=StatusResponse)
async def update_ui_preferences(
    request: UIPreferencesRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Update user's UI preferences (persisted to DB for cross-device sync)."""
    from app.agent.memory.semantic import SemanticMemory
    memory = SemanticMemory(db, user_id)
    if request.theme:
        await memory.learn_fact("ui_preferences", "theme", request.theme, confidence=1.0, is_user_set=True)
    if request.language:
        await memory.learn_fact("ui_preferences", "language", request.language, confidence=1.0, is_user_set=True)
    if request.market_preference:
        await memory.learn_fact("ui_preferences", "market_preference", request.market_preference, confidence=1.0, is_user_set=True)
    return {"status": "updated"}
