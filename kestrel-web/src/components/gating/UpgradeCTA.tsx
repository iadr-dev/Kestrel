"use client";

import Link from "next/link";
import { Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import type { Tier } from "@/lib/entitlements";

interface Props {
  /** Tier that unlocks the gated content — drives the headline copy. */
  requiredTier?: Tier;
  /** Compact variant for inline/strip use (no big lock circle). */
  compact?: boolean;
}

/**
 * Lock badge + upgrade button, shared by every gated surface. Links to /pricing.
 * Copy lives in the `gating` i18n namespace (no product-internal jargon).
 */
export function UpgradeCTA({ requiredTier = "premium", compact = false }: Props) {
  const t = useTranslations("gating");
  const tierLabel = requiredTier === "pro" ? "Pro" : "Premium";

  return (
    <div className={`flex flex-col items-center text-center ${compact ? "gap-1.5" : "gap-2"}`}>
      {!compact && (
        <div className="w-11 h-11 rounded-full bg-raised/80 border border-border/60 flex items-center justify-center">
          <Lock className="w-5 h-5 text-signal" />
        </div>
      )}
      <p className="font-semibold text-sm text-foreground">
        {t("locked_title", { tier: tierLabel })}
      </p>
      {!compact && <p className="text-xs text-muted max-w-[15rem]">{t("locked_hint")}</p>}
      <Link
        href="/pricing"
        className="mt-1 inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-signal text-white text-xs font-semibold hover:opacity-90 transition-opacity"
      >
        {compact && <Lock className="w-3 h-3" />}
        {t("upgrade_cta")}
      </Link>
    </div>
  );
}
