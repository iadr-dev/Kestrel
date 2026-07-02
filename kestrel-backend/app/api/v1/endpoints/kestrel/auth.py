import json
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import UserTier
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_session
from app.dependencies import (
    get_auth_service,
    get_current_user_id,
    get_current_user_id_or_none,
    get_settings,
    is_admin_email,
)
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserMeResponse,
)
from app.services.platform.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from fastapi import HTTPException

    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await user_repo.create_with_password(
        email=request.email,
        password_hash=service.hash_password(request.password),
        display_name=request.display_name,
    )
    await db.commit()
    return {"message": "User registered", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from fastapi import HTTPException

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request.email)
    if not user or not service.verify_credentials(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Admins always get the top tier (rate/daily limits + feature gates) regardless
    # of the stored tier column, so an admin account isn't throttled at free-tier.
    tier = UserTier.PRO if is_admin_email(user.email) else user.tier
    return service.issue_tokens_for_user(user.id, tier=tier)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    return service.refresh_access_token(request.refresh_token)


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    link: bool = False,
    service: AuthService = Depends(get_auth_service),
    user_id: str | None = Depends(get_current_user_id_or_none),
) -> dict[str, str]:
    match provider:
        case "google":
            result = await service.get_google_authorize_url()
        case "line":
            result = await service.get_line_authorize_url()
        case _:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    # For account-linking, overwrite the pending state value with link metadata.
    if link and user_id:
        state = result.get("state", "")
        await service._remember_state(state, f"{provider}:link:{user_id}")

    return result


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(""),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    frontend_url = getattr(settings, "frontend_url", "http://localhost:3000")

    try:
        result = await service.process_oauth_callback(provider, code, state, db)
        tokens = result["tokens"]
        user_data = result["user_data"]
        user_data["is_admin"] = is_admin_email(user_data.get("email"))

        user_encoded = urllib.parse.quote(json.dumps(user_data))
        token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        return RedirectResponse(f"{frontend_url}/callback?token={token}&refresh_token={refresh_token}&user={user_encoded}")
    except Exception as e:
        # Log full detail server-side; return a generic code to the client (no internal leak).
        from app.core.logging import get_logger
        get_logger(__name__).warning("oauth_callback_failed", provider=provider, error=str(e)[:200])
        return RedirectResponse(f"{frontend_url}/login?error=oauth_failed")


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get current user profile with admin flag. Frontend uses this instead of checking emails locally."""
    user_repo = UserRepository(db)
    user = await user_repo.get_with_full_profile(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    from sqlalchemy import select

    from app.models.user import OAuthAccount
    stmt = select(OAuthAccount.provider).where(OAuthAccount.user_id == user_id)
    result = await db.execute(stmt)
    providers = [row[0] for row in result.all()]

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "picture_url": user.picture_url,
        "tier": user.tier,
        "providers": providers,
        "is_admin": is_admin_email(user.email),
    }
