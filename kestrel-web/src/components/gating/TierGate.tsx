"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { Tier } from "@/lib/entitlements";
import { UpgradeCTA } from "./UpgradeCTA";

interface Props {
  /** When false, the gate is inactive and children render normally (entitled user). */
  locked: boolean;
  /**
   * "teaser"  — frosted whole-card overlay + centered lock + upgrade CTA (AI blocks).
   * "partial" — render the (already-truncated) children + a blurred locked strip below
   *             with "再看 N 檔 · 升級解鎖" (data tables/rankings).
   */
  mode: "teaser" | "partial";
  requiredTier?: Tier;
  /** partial mode: how many more rows are hidden (for the "再看 N 檔" copy). */
  hiddenCount?: number;
  children: ReactNode;
}

/**
 * Single reusable gate with two display modes (matches the two reference patterns).
 * The frosted overlay is COSMETIC — the server already withheld the real data, so a
 * teaser card contains no sensitive values behind the blur.
 */
export function TierGate({ locked, mode, requiredTier = "premium", hiddenCount, children }: Props) {
  const t = useTranslations("gating");

  if (!locked) return <>{children}</>;

  if (mode === "teaser") {
    return (
      <div className="relative overflow-hidden rounded-2xl">
        {/* Blurred, non-interactive preview of the shell underneath. */}
        <div className="pointer-events-none select-none blur-sm opacity-60" aria-hidden>
          {children}
        </div>
        <div className="absolute inset-0 flex items-center justify-center bg-surface/40 backdrop-blur-[2px]">
          <UpgradeCTA requiredTier={requiredTier} />
        </div>
      </div>
    );
  }

  // partial: visible rows already rendered by the caller; append a locked strip.
  return (
    <div>
      {children}
      <div className="relative mt-1 rounded-xl overflow-hidden border border-border/40">
        <div className="px-4 py-5 flex flex-col items-center gap-2 bg-raised/40 backdrop-blur-[1px]">
          {typeof hiddenCount === "number" && hiddenCount > 0 && (
            <p className="text-xs text-muted">{t("more_rows", { count: hiddenCount })}</p>
          )}
          <UpgradeCTA requiredTier={requiredTier} compact />
        </div>
      </div>
    </div>
  );
}
