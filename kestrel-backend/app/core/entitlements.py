"""Feature entitlements — the SINGLE source of truth for tier-based access.

Everything tier-gated in the product answers to this module. The server computes the
`feature-key -> bool` answers here; the frontend only *reads* them (via /entitlements
or the profile payload) and never re-implements the tier math. This prevents drift
between the two codebases.

Gating scope (product decision): ONLY AI features + sponsor-level (paid) datasets are
gated. Watchlist, TW/US market coverage, tech charts, news and peers are free for all.

BYOK (bring-your-own-key): a user who supplies their own LLM key pays their own inference
cost, so their AI chat limit is removed on every tier (chat_limit_for returns None).
"""

from typing import Any

from app.core.constants import UserTier

# Feature keys — the canonical identifiers shared with the frontend (mirror the union
# in kestrel-web/src/lib/entitlements.ts). Add a key here + there together.
FeatureKey = str

# feature-key -> minimum tier required to ACCESS it (unlocked view / full data).
# Anything not listed is free for everyone.
FEATURE_MIN_TIER: dict[FeatureKey, UserTier] = {
    # --- AI features (premium) ---
    "ai_score": UserTier.PREMIUM,
    "ai_summary": UserTier.PREMIUM,
    "ai_swot": UserTier.PREMIUM,
    "news_sentiment": UserTier.PREMIUM,      # sentiment + 割韭菜 divergence flag
    # --- Sponsor-level (paid) datasets (premium) ---
    "sponsor_dataset": UserTier.PREMIUM,     # deep chip / institutional flow tables
    # --- Pro-only ---
    "deep_research": UserTier.PRO,           # multi-agent deep research
    "realtime": UserTier.PRO,                # realtime / priority AI
    "main_force": UserTier.PRO,              # 主力分點 tracker
}

# Daily AI-chat limits per tier (free models for FREE; managed paid quota above).
# BYOK removes the limit entirely (see chat_limit_for).
CHAT_LIMITS: dict[str, int] = {
    UserTier.FREE: 3,
    UserTier.PREMIUM: 100,
    UserTier.PRO: 999999,
}

# Rows a FREE user sees before the locked "upgrade" strip on a sponsor-level table.
FREE_PREVIEW_ROWS = 5

# Tier ordering for hierarchical comparisons (free < premium < pro).
_TIER_ORDER: dict[str, int] = {UserTier.FREE: 0, UserTier.PREMIUM: 1, UserTier.PRO: 2}


def has_access(feature: FeatureKey, tier: str) -> bool:
    """True if `tier` may access `feature` (unlocked). Unlisted features are free."""
    required = FEATURE_MIN_TIER.get(feature)
    if required is None:
        return True
    return _TIER_ORDER.get(tier, 0) >= _TIER_ORDER.get(required, 0)


def required_tier(feature: FeatureKey) -> str | None:
    """The minimum tier for `feature`, or None if it is free for everyone."""
    req = FEATURE_MIN_TIER.get(feature)
    return str(req) if req is not None else None


def chat_limit_for(tier: str, has_user_keys: bool = False) -> int | None:
    """Daily AI-chat limit for `tier`. None means unlimited.

    BYOK (has_user_keys) removes the cap on every tier — the user pays their own
    inference cost, so we don't meter it.
    """
    if has_user_keys:
        return None
    return CHAT_LIMITS.get(tier, CHAT_LIMITS[UserTier.FREE])


def gate_rows(
    rows: list[Any], tier: str, feature: FeatureKey = "sponsor_dataset"
) -> dict[str, Any]:
    """Partial-payload gate for sponsor-level tables.

    Entitled tiers get all rows. A tier without access gets only the first
    FREE_PREVIEW_ROWS, with `locked`/`total`/`required_tier` so the frontend can render
    the "show top N, blur the rest + upgrade" strip.
    """
    if has_access(feature, tier):
        return {"rows": rows, "locked": False, "total": len(rows), "required_tier": None}
    return {
        "rows": rows[:FREE_PREVIEW_ROWS],
        "locked": True,
        "total": len(rows),
        "required_tier": required_tier(feature),
    }


def entitlements_for(tier: str, has_user_keys: bool = False, chat_used: int = 0) -> dict[str, Any]:
    """The entitlements payload the client consumes.

    Shape:
        {
          "tier": "free",
          "has_user_keys": false,
          "chat_limit": 3 | null,     # null = unlimited (BYOK)
          "chat_used": 0,
          "features": { "ai_score": false, "ai_summary": false, ... }
        }
    """
    return {
        "tier": tier,
        "has_user_keys": has_user_keys,
        "chat_limit": chat_limit_for(tier, has_user_keys),
        "chat_used": chat_used,
        "features": {key: has_access(key, tier) for key in FEATURE_MIN_TIER},
    }
