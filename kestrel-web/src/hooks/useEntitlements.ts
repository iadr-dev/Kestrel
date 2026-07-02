"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import {
  DEFAULT_ENTITLEMENTS,
  FEATURE_REQUIRED_TIER,
  type Entitlements,
  type FeatureKey,
  type Tier,
} from "@/lib/entitlements";

interface ProfileWithEntitlements {
  tier?: string;
  entitlements?: Entitlements;
}

/**
 * Reads server-computed feature entitlements off the user profile. The client NEVER
 * computes tier math — it consumes `entitlements.features[key]`. Anonymous users fall
 * back to the free default (nothing unlocked), so gated surfaces render their teaser.
 */
export function useEntitlements() {
  const authed = isAuthenticated();

  const { data, isLoading } = useQuery({
    queryKey: ["/user/profile", "entitlements"],
    queryFn: () => apiFetch<ProfileWithEntitlements>("/user/profile"),
    enabled: authed,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const ent: Entitlements = data?.entitlements ?? DEFAULT_ENTITLEMENTS;

  return {
    entitlements: ent,
    loading: authed && isLoading,
    tier: ent.tier as Tier,
    hasKeys: ent.has_user_keys,
    chatLimit: ent.chat_limit, // null = unlimited (BYOK)
    chatUsed: ent.chat_used,
    /** True if the user's tier unlocks `feature`. */
    can: (feature: FeatureKey): boolean => ent.features[feature] ?? false,
    /** The tier that unlocks `feature` (for upgrade CTA copy). */
    requiredTier: (feature: FeatureKey): Tier => FEATURE_REQUIRED_TIER[feature],
  };
}
