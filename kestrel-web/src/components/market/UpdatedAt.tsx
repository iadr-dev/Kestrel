"use client";

import { useTranslations } from "next-intl";
import { formatDateTime } from "@/lib/date";

/** Small "資料更新 YYYY-MM-DD HH:mm:ss" badge for cron-/ingest-fed views, so users
 *  can see how fresh the data is. Pass React Query's `dataUpdatedAt` (epoch ms).
 *  Renders nothing until the first successful fetch. */
export function UpdatedAt({ ms, className = "" }: { ms: number | null | undefined; className?: string }) {
  const t = useTranslations("data");
  const stamp = formatDateTime(ms);
  if (!stamp) return null;
  return (
    <span className={`text-[10px] text-muted/70 font-mono ${className}`} title={stamp}>
      {t("updated_at")} {stamp}
    </span>
  );
}
