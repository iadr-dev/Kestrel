"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEntitlements } from "@/hooks/useEntitlements";
import type { Tier } from "@/lib/entitlements";

type Cycle = "monthly" | "annual";

interface PlanDef {
  tier: Tier;
  name: string;
  recommended?: boolean;
  // Price i18n-key suffixes; free has a single flat price.
  price: (cycle: Cycle, byok: boolean) => string;
  features: string[];
}

export default function PricingPage() {
  const t = useTranslations("pricing");
  const { tier: currentTier } = useEntitlements();
  const [cycle, setCycle] = useState<Cycle>("annual");
  // BYOK is per-tier: each paid card has its own checkbox that swaps the price column.
  const [byok, setByok] = useState<Record<Tier, boolean>>({ free: false, premium: false, pro: false });

  const suffix = cycle === "monthly" ? t("per_month") : t("per_year");

  const plans: PlanDef[] = [
    {
      tier: "free",
      name: t("tier_free"),
      price: () => t("free_price"),
      features: [t("f_market_data"), t("f_unlimited_watchlist"), t("f_tech_charts"), t("f_ai_chat_free")],
    },
    {
      tier: "premium",
      name: t("tier_premium"),
      recommended: true,
      price: (c, b) => t(`premium_${b ? "byok" : "managed"}_${c === "monthly" ? "mo" : "yr"}`),
      features: [
        t("f_ai_score_summary"),
        t("f_advanced_data"),
        t("f_news_sentiment"),
        t("f_ai_chat_managed"),
        t("f_ai_chat_unlimited_byok"),
      ],
    },
    {
      tier: "pro",
      name: t("tier_pro"),
      price: (c, b) => t(`pro_${b ? "byok" : "managed"}_${c === "monthly" ? "mo" : "yr"}`),
      features: [t("f_deep_research"), t("f_realtime"), t("f_main_force"), t("f_ai_chat_unlimited_byok")],
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-center">{t("title")}</h1>
      <p className="mt-2 text-sm text-muted text-center max-w-xl mx-auto">{t("subtitle")}</p>

      {/* Monthly / annual toggle */}
      <div className="mt-6 flex items-center justify-center gap-2">
        <div className="inline-flex rounded-full border border-border/50 p-1 bg-surface">
          {(["monthly", "annual"] as Cycle[]).map((c) => (
            <button
              key={c}
              onClick={() => setCycle(c)}
              className={`px-4 py-1.5 text-xs font-medium rounded-full transition-colors ${
                cycle === c ? "bg-signal text-white" : "text-muted hover:text-foreground"
              }`}
            >
              {t(c === "monthly" ? "billing_monthly" : "billing_annual")}
              {c === "annual" && (
                <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-up/15 text-up">
                  {t("annual_save")}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 grid md:grid-cols-3 gap-4">
        {plans.map((plan) => {
          const isPaid = plan.tier !== "free";
          const b = byok[plan.tier];
          const isCurrent = currentTier === plan.tier;
          return (
            <div
              key={plan.tier}
              className={`relative rounded-2xl border p-6 flex flex-col ${
                plan.recommended ? "border-signal shadow-lg" : "border-border/40"
              }`}
            >
              {plan.recommended && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-signal text-white text-[10px] font-bold">
                  {t("recommended")}
                </span>
              )}
              <h3 className="font-semibold">{plan.name}</h3>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-signal font-mono">{plan.price(cycle, b)}</span>
                {isPaid && <span className="text-xs text-muted">{suffix}</span>}
              </div>

              {isPaid && (
                <label className="mt-3 flex items-start gap-2 text-xs text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={b}
                    onChange={(e) => setByok((prev) => ({ ...prev, [plan.tier]: e.target.checked }))}
                    className="mt-0.5 accent-signal"
                  />
                  <span>
                    <span className="font-medium text-foreground">{t("byok_label")}</span>
                    <span className="block">{t("byok_hint")}</span>
                  </span>
                </label>
              )}

              <ul className="mt-4 space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-xs">
                    <Check className="w-3.5 h-3.5 text-up shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <div className="mt-5 text-center text-xs py-2 rounded-full bg-raised text-muted font-medium">
                  {t("current_plan")}
                </div>
              ) : (
                <Link
                  href="/dashboard/settings?section=5"
                  className={`mt-5 text-center text-sm py-2 rounded-full font-semibold transition-opacity hover:opacity-90 ${
                    plan.recommended ? "bg-signal text-white" : "border border-border/60 text-foreground"
                  }`}
                >
                  {isPaid ? t("cta_upgrade") : t("cta_free")}
                </Link>
              )}
            </div>
          );
        })}
      </div>

      <p className="mt-6 flex items-center justify-center gap-1.5 text-[11px] text-muted">
        <Lock className="w-3 h-3" />
        {t("placeholder_note")}
      </p>
    </div>
  );
}
