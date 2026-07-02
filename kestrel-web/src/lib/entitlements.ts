/**
 * Feature entitlements — client-side TYPE mirror of the backend source of truth
 * (kestrel-backend/app/core/entitlements.py).
 *
 * IMPORTANT: this file mirrors the feature-key UNION + payload shape ONLY. It does NOT
 * re-implement the tier math — the server computes every `feature -> bool` answer and
 * the client just reads `entitlements.features[key]`. Keeping the key union here lets
 * `tsc` catch drift if the backend adds/removes a feature key.
 */

export type FeatureKey =
  | "ai_score"
  | "ai_summary"
  | "ai_swot"
  | "news_sentiment"
  | "sponsor_dataset"
  | "deep_research"
  | "realtime"
  | "main_force";

export type Tier = "free" | "premium" | "pro";

export interface Entitlements {
  tier: Tier;
  has_user_keys: boolean;
  /** null = unlimited (BYOK). */
  chat_limit: number | null;
  chat_used: number;
  features: Record<FeatureKey, boolean>;
}

/** Safe default before the profile/entitlements payload has loaded: free, nothing unlocked. */
export const DEFAULT_ENTITLEMENTS: Entitlements = {
  tier: "free",
  has_user_keys: false,
  chat_limit: 3,
  chat_used: 0,
  features: {
    ai_score: false,
    ai_summary: false,
    ai_swot: false,
    news_sentiment: false,
    sponsor_dataset: false,
    deep_research: false,
    realtime: false,
    main_force: false,
  },
};

/** The tier that unlocks a given feature (for upgrade-CTA copy). Mirror of backend map. */
export const FEATURE_REQUIRED_TIER: Record<FeatureKey, Tier> = {
  ai_score: "premium",
  ai_summary: "premium",
  ai_swot: "premium",
  news_sentiment: "premium",
  sponsor_dataset: "premium",
  deep_research: "pro",
  realtime: "pro",
  main_force: "pro",
};
