"""Tests for UserRepository — including the C2 fix (password persistence).

Before the fix, register_user() computed a hash but never persisted it, and
login verified against an empty string — local login could never work. These
tests assert the create_with_password / get_by_email round-trip works and that
credential verification behaves correctly.

Run: pytest tests/database/test_user_repo.py -v
"""

import pytest

from app.db.repositories.user_repo import UserRepository
from app.services.platform.auth_service import AuthService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def auth_service():
    from app.core.config import Settings
    return AuthService(Settings())


class TestPasswordPersistence:
    async def test_create_with_password_persists_hash(self, session, auth_service):
        repo = UserRepository(session)
        pw_hash = auth_service.hash_password("s3cret-pw")
        user = await repo.create_with_password(
            email="alice@example.com", password_hash=pw_hash, display_name="Alice"
        )
        await session.commit()

        assert user.id
        assert user.email == "alice@example.com"
        assert user.password_hash == pw_hash
        assert user.tier == "free"  # default

    async def test_get_by_email_round_trip(self, session, auth_service):
        repo = UserRepository(session)
        await repo.create_with_password(
            email="bob@example.com",
            password_hash=auth_service.hash_password("hunter2"),
            display_name="Bob",
        )
        await session.commit()

        fetched = await repo.get_by_email("bob@example.com")
        assert fetched is not None
        assert fetched.email == "bob@example.com"

    async def test_credential_verification(self, session, auth_service):
        repo = UserRepository(session)
        await repo.create_with_password(
            email="carol@example.com",
            password_hash=auth_service.hash_password("correct-horse"),
        )
        await session.commit()

        user = await repo.get_by_email("carol@example.com")
        assert auth_service.verify_credentials("correct-horse", user.password_hash) is True
        assert auth_service.verify_credentials("wrong", user.password_hash) is False

    async def test_verify_rejects_empty_hash(self, auth_service):
        """Regression guard: the old bug verified against '' (always failed/insecure)."""
        assert auth_service.verify_credentials("anything", "") is False
        assert auth_service.verify_credentials("anything", None) is False


class TestTokenIssuance:
    async def test_tokens_use_user_id_as_subject(self, session, auth_service):
        """C2: tokens should be keyed on user.id (consistent with OAuth path)."""
        repo = UserRepository(session)
        user = await repo.create_with_password(
            email="dave@example.com",
            password_hash=auth_service.hash_password("pw"),
        )
        await session.commit()

        tokens = auth_service.issue_tokens_for_user(user.id, tier=user.tier)
        assert tokens["access_token"]
        assert tokens["refresh_token"]
        assert tokens["token_type"] == "bearer"

        from app.core.config import Settings
        from app.core.security import decode_token
        payload = decode_token(tokens["access_token"], Settings())
        assert payload["sub"] == user.id
