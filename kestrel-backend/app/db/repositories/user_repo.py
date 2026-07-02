from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.user import OAuthAccount, User


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.oauth_accounts))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_oauth(self, provider: str, provider_user_id: str) -> User | None:
        stmt = (
            select(User)
            .join(User.oauth_accounts)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
            .options(selectinload(User.oauth_accounts))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_full_profile(self, user_id: str) -> User | None:
        """Load user with all related data in one query (avoids N+1)."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.oauth_accounts),
                selectinload(User.portfolios),
                selectinload(User.watchlists),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_with_password(
        self,
        email: str,
        password_hash: str,
        display_name: str | None = None,
    ) -> User:
        """Create a local (email/password) user."""
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def create_with_oauth(
        self,
        email: str | None,
        display_name: str | None,
        picture_url: str | None,
        provider: str,
        provider_user_id: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> User:
        user = User(
            email=email,
            display_name=display_name,
            picture_url=picture_url,
        )
        oauth = OAuthAccount(
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        user.oauth_accounts.append(oauth)
        self._session.add(user)
        await self._session.flush()
        return user

    async def link_oauth(
        self,
        user: User,
        provider: str,
        provider_user_id: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> OAuthAccount:
        oauth = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        self._session.add(oauth)
        await self._session.flush()
        return oauth
