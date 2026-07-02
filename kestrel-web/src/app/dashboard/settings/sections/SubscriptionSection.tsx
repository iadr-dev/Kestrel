"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { logError } from "@/lib/log";

export function SubscriptionSection() {
  const t = useTranslations("settings.subscription");
  const tp = useTranslations("pricing");
  // Seed tier from localStorage (fast), then verify from API (source of truth).
  const [userTier, setUserTier] = useState(() => {
    if (typeof window === "undefined") return "free";
    try {
      const raw = localStorage.getItem("kestrel_user");
      return (raw && JSON.parse(raw).tier) || "free";
    } catch { return "free"; }
  });

  useEffect(() => {
    apiFetch<{ id: string; tier: string }>("/user/profile")
      .then((res) => { if (res.tier) setUserTier(res.tier); })
      .catch((err) => logError("SubscriptionSection.load", err));
  }, []);

  const plans = [
    { name: "Free", price: t("free_price"), features: ["60 req/min", t("f_1_portfolio"), t("f_10_watchlist")] },
    { name: "Premium", price: t("premium_price"), features: ["300 req/min", t("f_10_portfolio"), t("f_50_watchlist"), t("f_advanced_screener")] },
    { name: "Pro", price: t("pro_price"), features: ["600 req/min", t("f_unlimited_portfolio"), t("f_realtime"), t("f_main_force")] },
  ];
  return (
    <div>
      <h2 className="text-lg font-bold mb-4">{t("title")}</h2>
      <div className="inline-block px-3 py-1 text-xs bg-raised rounded font-mono mb-4 uppercase">{userTier}</div>
      <div className="grid md:grid-cols-3 gap-4">
        {plans.map((plan) => (
          <div key={plan.name} className="border border-border/40 rounded-2xl p-5">
            <h3 className="font-semibold mb-1">{plan.name}</h3>
            <p className="text-signal font-mono text-lg mb-3">{plan.price}</p>
            <ul className="space-y-1">
              {plan.features.map((f) => (
                <li key={f} className="text-xs text-muted">✓ {f}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <Link
        href="/pricing"
        className="mt-4 inline-flex items-center gap-1.5 text-sm text-signal font-medium hover:underline"
      >
        {tp("title")}
        <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}
