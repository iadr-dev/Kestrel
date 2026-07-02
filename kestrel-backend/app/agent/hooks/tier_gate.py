"""Tier gate hook — blocks premium features for free-tier users."""

from app.core.constants import TIER_FEATURES, UserTier
from app.core.entitlements import chat_limit_for, has_access, required_tier
from app.core.exceptions import TierInsufficientError
from app.core.logging import get_logger

logger = get_logger(__name__)


class TierGate:
    """Enforces feature limits based on user tier."""

    def check_chat_limit(self, user_tier: str, chats_today: int, has_user_keys: bool = False) -> None:
        """Raise if user has exceeded daily chat limit for their tier.

        BYOK (has_user_keys) removes the cap — the user pays their own inference cost.
        """
        limit = chat_limit_for(user_tier, has_user_keys)
        if limit is None:
            return  # unlimited (BYOK)
        if chats_today >= limit:
            raise TierInsufficientError(
                message=f"Daily chat limit reached ({limit} for {user_tier} tier). Upgrade or add your own API key for more.",
                detail={"limit": limit, "used": chats_today, "tier": user_tier},
            )

    def check_feature(self, feature_key: str, user_tier: str) -> None:
        """Raise if `user_tier` cannot access `feature_key` (hard gate)."""
        if not has_access(feature_key, user_tier):
            req = required_tier(feature_key)
            raise TierInsufficientError(
                message=f"This feature requires {req} tier (current: {user_tier})",
                detail={"required_tier": req, "current_tier": user_tier, "feature": feature_key},
            )

    def check_skill_access(self, skill_tier: str, user_tier: str) -> None:
        """Raise if user's tier is insufficient for this skill."""
        tier_order: dict[str, int] = {UserTier.FREE: 0, UserTier.PREMIUM: 1, UserTier.PRO: 2}
        required = tier_order.get(skill_tier, 0)
        current = tier_order.get(user_tier, 0)
        if current < required:
            raise TierInsufficientError(
                message=f"This feature requires {skill_tier} tier (current: {user_tier})",
                detail={"required_tier": skill_tier, "current_tier": user_tier},
            )

    def check_portfolio_limit(self, user_tier: str, current_count: int) -> None:
        """Check if user can create more portfolios."""
        limits = TIER_FEATURES.get(user_tier, TIER_FEATURES[UserTier.FREE])
        max_portfolios = limits["max_portfolios"]
        if current_count >= max_portfolios:
            raise TierInsufficientError(
                message=f"Portfolio limit reached ({max_portfolios} for {user_tier} tier)",
                detail={"limit": max_portfolios, "current": current_count, "tier": user_tier},
            )

    def check_watchlist_limit(self, user_tier: str, current_count: int) -> None:
        """Check if user can add more stocks to watchlist."""
        limits = TIER_FEATURES.get(user_tier, TIER_FEATURES[UserTier.FREE])
        max_stocks = limits["max_watchlist_stocks"]
        if current_count >= max_stocks:
            raise TierInsufficientError(
                message=f"Watchlist limit reached ({max_stocks} stocks for {user_tier} tier)",
                detail={"limit": max_stocks, "current": current_count, "tier": user_tier},
            )

    def check_indicator_limit(self, user_tier: str, requested_count: int) -> None:
        """Check if user can request this many indicators at once."""
        limits = TIER_FEATURES.get(user_tier, TIER_FEATURES[UserTier.FREE])
        max_indicators = limits["max_indicators"]
        if requested_count > max_indicators:
            raise TierInsufficientError(
                message=f"Indicator limit: {max_indicators} per request for {user_tier} tier",
                detail={"limit": max_indicators, "requested": requested_count, "tier": user_tier},
            )
