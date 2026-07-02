"""Telegram webhook secret token verification."""

import hmac

from fastapi import Request

from app.core.config import Environment, Settings


def verify_telegram_secret(request: Request, secret_token: str) -> bool:
    """Verify X-Telegram-Bot-Api-Secret-Token header.

    Fail-closed in non-dev environments: if no secret is configured, the webhook
    is REJECTED rather than left open (the previous behaviour accepted any caller
    when the secret was unset, which is an auth bypass in production). Only the
    development environment keeps the no-secret convenience.
    """
    if not secret_token:
        return Settings().environment == Environment.DEVELOPMENT
    header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return hmac.compare_digest(header_token, secret_token)
