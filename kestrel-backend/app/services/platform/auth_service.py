"""Auth service — JWT issuance, Google OAuth, LINE Login with PKCE."""

import urllib.parse
from typing import Any, cast

import httpx

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_pkce_pair,
    generate_state,
    hash_password,
    verify_password,
)


class AuthService:
    # Pending OAuth states expire after this many seconds (login flow is short-lived).
    _STATE_TTL = 600
    # In-memory fallback cap (only used when no shared cache is configured).
    _MAX_PENDING_STATES = 1000

    def __init__(self, settings: Settings, cache: Any | None = None) -> None:
        self._settings = settings
        self._cache = cache  # CacheBackend (Redis or in-memory) — shared across workers
        # Per-process fallback used only when no cache backend is provided.
        self._pkce_store: dict[str, str] = {}
        self._state_store: dict[str, str] = {}

    @staticmethod
    def _state_key(state: str) -> str:
        return f"oauth:state:{state}"

    @staticmethod
    def _pkce_key(state: str) -> str:
        return f"oauth:pkce:{state}"

    async def _remember_state(self, state: str, value: str, code_verifier: str | None = None) -> None:
        """Record a pending OAuth state (shared cache with TTL when available)."""
        if self._cache is not None:
            await self._cache.set(self._state_key(state), value, ttl=self._STATE_TTL)
            if code_verifier is not None:
                await self._cache.set(self._pkce_key(state), code_verifier, ttl=self._STATE_TTL)
            return
        # In-memory fallback: evict oldest if over capacity.
        while len(self._state_store) >= self._MAX_PENDING_STATES:
            oldest = next(iter(self._state_store))
            self._state_store.pop(oldest, None)
            self._pkce_store.pop(oldest, None)
        self._state_store[state] = value
        if code_verifier is not None:
            self._pkce_store[state] = code_verifier

    async def _get_state(self, state: str) -> str | None:
        if self._cache is not None:
            return cast(str | None, await self._cache.get(self._state_key(state)))
        return self._state_store.get(state)

    async def _consume_state(self, state: str) -> tuple[str | None, str | None]:
        """Atomically read+remove a state and its PKCE verifier."""
        if self._cache is not None:
            value = await self._cache.get(self._state_key(state))
            verifier = await self._cache.get(self._pkce_key(state))
            await self._cache.delete(self._state_key(state))
            await self._cache.delete(self._pkce_key(state))
            return value, verifier
        value = self._state_store.pop(state, None)
        verifier = self._pkce_store.pop(state, None)
        return value, verifier

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password for storage."""
        return hash_password(password)

    def verify_credentials(self, password: str, stored_hash: str | None) -> bool:
        """Verify a plaintext password against a stored bcrypt hash."""
        if not stored_hash:
            return False
        return verify_password(password, stored_hash)

    def issue_tokens_for_user(self, user_id: str, tier: str = "free") -> dict[str, str | int]:
        """Issue access+refresh tokens for an authenticated user id."""
        return self._issue_tokens(sub=user_id, tier=tier)

    def refresh_access_token(self, refresh_token: str) -> dict[str, str | int]:
        payload = decode_token(refresh_token, self._settings)
        if payload is None or payload.get("type") != "refresh":
            raise AuthenticationError(message="Invalid refresh token")
        return self._issue_tokens(sub=payload["sub"], tier=payload.get("tier", "free"))

    # --- Google OAuth ---

    async def get_google_authorize_url(self) -> dict[str, str]:
        state = generate_state()
        await self._remember_state(state, "google")
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return {"authorization_url": url, "state": state}

    async def handle_google_callback(self, code: str, state: str) -> dict[str, Any]:
        value, _ = await self._consume_state(state)
        if value is None:
            raise AuthenticationError(message="Invalid OAuth state")

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "redirect_uri": self._settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise AuthenticationError(message="Google token exchange failed")
            token_data = token_resp.json()

            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if userinfo_resp.status_code != 200:
                raise AuthenticationError(message="Failed to fetch Google user info")
            user_info = userinfo_resp.json()

        tokens = self._issue_tokens(sub=user_info["email"])
        return {
            **tokens,
            "user": {
                "id": user_info.get("sub"),
                "email": user_info.get("email"),
                "display_name": user_info.get("name"),
                "picture_url": user_info.get("picture"),
                "provider": "google",
            },
        }

    # --- LINE Login (PKCE) ---

    async def get_line_authorize_url(self) -> dict[str, str]:
        state = generate_state()
        code_verifier, code_challenge = generate_pkce_pair()
        await self._remember_state(state, "line", code_verifier=code_verifier)

        params = {
            "response_type": "code",
            "client_id": self._settings.line_channel_id,
            "redirect_uri": self._settings.line_redirect_uri,
            "state": state,
            "scope": "profile openid email",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = f"https://access.line.me/oauth2/v2.1/authorize?{urllib.parse.urlencode(params)}"
        return {"authorization_url": url, "state": state}

    async def handle_line_callback(self, code: str, state: str) -> dict[str, Any]:
        value, code_verifier = await self._consume_state(state)
        if value is None:
            raise AuthenticationError(message="Invalid OAuth state")

        if not code_verifier:
            raise AuthenticationError(message="PKCE verifier not found")

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://api.line.me/oauth2/v2.1/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._settings.line_redirect_uri,
                    "client_id": self._settings.line_channel_id,
                    "client_secret": self._settings.line_channel_secret,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_resp.status_code != 200:
                raise AuthenticationError(
                    message="LINE token exchange failed",
                    detail={"line_error": token_resp.text},
                )
            token_data = token_resp.json()

            # Verify ID token to get user profile
            verify_resp = await client.post(
                "https://api.line.me/oauth2/v2.1/verify",
                data={
                    "id_token": token_data["id_token"],
                    "client_id": self._settings.line_channel_id,
                },
            )
            if verify_resp.status_code != 200:
                raise AuthenticationError(message="LINE ID token verification failed")
            id_token_data = verify_resp.json()

        user_id = id_token_data.get("sub", "")
        email = id_token_data.get("email")
        tokens = self._issue_tokens(sub=user_id)
        return {
            **tokens,
            "user": {
                "id": user_id,
                "email": email,
                "display_name": id_token_data.get("name"),
                "picture_url": id_token_data.get("picture"),
                "provider": "line",
            },
        }

    # --- Internal ---

    def _issue_tokens(self, sub: str, tier: str = "free") -> dict[str, str | int]:
        access = create_access_token({"sub": sub, "tier": tier}, self._settings)
        refresh = create_refresh_token({"sub": sub, "tier": tier}, self._settings)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": self._settings.jwt_access_token_expire_minutes * 60,
        }

    async def process_oauth_callback(
        self, provider: str, code: str, state: str, db: Any
    ) -> dict[str, Any]:
        """Handle full OAuth callback: exchange code, upsert user, issue tokens.

        Returns dict with tokens + user_data for frontend redirect.
        """
        from sqlalchemy import select

        from app.db.repositories.user_repo import UserRepository
        from app.models.user import OAuthAccount

        # Check if this is a link operation (peek before the handler consumes it).
        link_user_id: str | None = None
        state_data = await self._get_state(state) or ""
        if isinstance(state_data, str) and ":link:" in state_data:
            link_user_id = state_data.split(":link:")[1]

        # Exchange code for user info
        match provider:
            case "google":
                result = await self.handle_google_callback(code, state)
            case "line":
                result = await self.handle_line_callback(code, state)
            case _:
                raise AuthenticationError(f"Unsupported provider: {provider}")

        user_info = result.get("user", {})
        provider_user_id = user_info.get("id", "")
        email = user_info.get("email")
        display_name = user_info.get("display_name")
        picture_url = user_info.get("picture_url")

        user_repo = UserRepository(db)

        if link_user_id:
            from app.models.user import User
            link_user = await db.get(User, link_user_id)
            if link_user:
                existing_oauth = await user_repo.get_by_oauth(provider, provider_user_id)
                if not existing_oauth:
                    await user_repo.link_oauth(link_user, provider, provider_user_id, access_token=result.get("access_token"))
                if display_name and not link_user.display_name:
                    link_user.display_name = display_name
                if picture_url and not link_user.picture_url:
                    link_user.picture_url = picture_url
            db_user_id = link_user_id
        else:
            existing_user = await user_repo.get_by_oauth(provider, provider_user_id)

            if existing_user:
                if display_name and existing_user.display_name != display_name:
                    existing_user.display_name = display_name
                if picture_url and existing_user.picture_url != picture_url:
                    existing_user.picture_url = picture_url
                if email and existing_user.email != email:
                    existing_user.email = email
                db_user_id = existing_user.id
            elif email:
                email_user = await user_repo.get_by_email(email)
                if email_user:
                    await user_repo.link_oauth(
                        email_user, provider, provider_user_id,
                        access_token=result.get("access_token"),
                    )
                    email_user.display_name = display_name or email_user.display_name
                    email_user.picture_url = picture_url or email_user.picture_url
                    db_user_id = email_user.id
                else:
                    new_user = await user_repo.create_with_oauth(
                        email=email, display_name=display_name, picture_url=picture_url,
                        provider=provider, provider_user_id=provider_user_id,
                        access_token=result.get("access_token"),
                    )
                    db_user_id = new_user.id
            else:
                new_user = await user_repo.create_with_oauth(
                    email=None, display_name=display_name, picture_url=picture_url,
                    provider=provider, provider_user_id=provider_user_id,
                    access_token=result.get("access_token"),
                )
                db_user_id = new_user.id

        # Issue tokens
        tokens = self._issue_tokens(sub=db_user_id)

        # Get connected providers
        stmt = select(OAuthAccount.provider).where(OAuthAccount.user_id == db_user_id)
        oauth_result = await db.execute(stmt)
        connected_providers = [row[0] for row in oauth_result.all()]

        # Get latest user info
        db_user = await user_repo.get_with_full_profile(db_user_id)
        user_data = {
            "id": db_user_id,
            "email": db_user.email if db_user else email,
            "display_name": db_user.display_name if db_user else display_name,
            "picture_url": db_user.picture_url if db_user else picture_url,
            "provider": provider,
            "providers": connected_providers,
        }

        # Update login streak
        try:
            from datetime import date as date_cls
            from datetime import timedelta

            from app.models.pet import UserPetStats
            stmt_stats = select(UserPetStats).where(UserPetStats.user_id == db_user_id)
            stats_result = await db.execute(stmt_stats)
            stats = stats_result.scalar_one_or_none()
            if stats:
                today_str = str(date_cls.today())
                if stats.last_login_date != today_str:
                    yesterday = str(date_cls.today() - timedelta(days=1))
                    if stats.last_login_date == yesterday:
                        stats.streak_days += 1
                    else:
                        stats.streak_days = 1
                    stats.last_login_date = today_str
                    if stats.streak_days % 7 == 0:
                        stats.available_pulls += 1
                    await db.flush()
        except Exception:
            pass

        return {
            "tokens": tokens,
            "user_data": user_data,
        }
