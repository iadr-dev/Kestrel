import hashlib
import secrets
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.core.config import Settings

# We call bcrypt directly rather than via passlib: passlib 1.7.4 (unmaintained
# since 2020) crashes on bcrypt >= 4.1 during backend init. bcrypt produces and
# verifies the standard "$2b$" format, so hashes created by the old passlib path
# still verify here.
_BCRYPT_MAX_BYTES = 72  # bcrypt only considers the first 72 bytes of the secret


def _to_secret(password: str) -> bytes:
    """Encode and clamp to bcrypt's 72-byte limit (bcrypt 5.x raises past it)."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_secret(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_secret(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict[str, Any], settings: Settings) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    token: str = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(data: dict[str, Any], settings: Settings) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    token: str = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str, settings: Settings) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# --- PKCE helpers (for LINE Login) ---


def generate_pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) for S256 PKCE."""
    verifier_bytes = secrets.token_bytes(32)
    code_verifier = urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")
    challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = urlsafe_b64encode(challenge_digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def generate_state() -> str:
    return secrets.token_urlsafe(32)
