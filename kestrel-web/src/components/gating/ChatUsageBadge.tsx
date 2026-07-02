"use client";

import Link from "next/link";
import { Infinity as InfinityIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEntitlements } from "@/hooks/useEntitlements";

/**
 * Small "今日 2/3" AI-chat usage badge near the composer. Shows 無限制 when the user
 * has BYOK (chatLimit === null); turns into an upgrade nudge once the daily cap is hit.
 */
export function ChatUsageBadge() {
  const t = useTranslations("gating");
  const { chatLimit, chatUsed } = useEntitlements();

  if (chatLimit === null) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-muted">
        <InfinityIcon className="w-3 h-3" />
        {t("chat_unlimited")}
      </span>
    );
  }

  const reached = chatUsed >= chatLimit;
  if (reached) {
    return (
      <Link href="/pricing" className="text-[11px] font-medium text-signal hover:underline">
        {t("chat_limit_reached")}
      </Link>
    );
  }
  return (
    <span className="text-[11px] text-muted">
      {t("chat_usage", { used: chatUsed, limit: chatLimit })}
    </span>
  );
}
