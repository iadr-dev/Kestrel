"use client";

import { useTranslations } from "next-intl";

interface DataFreshnessBadgeProps {
  updatedAt: string | Date | null;
}

export function DataFreshnessBadge({ updatedAt }: DataFreshnessBadgeProps) {
  const t = useTranslations("data");

  if (!updatedAt) return null;

  const date = typeof updatedAt === "string" ? new Date(updatedAt) : updatedAt;
  if (isNaN(date.getTime())) return null;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMin / 60);

  let label: string;
  if (diffMin < 1) {
    label = t("just_now");
  } else if (diffMin < 60) {
    label = t("minutes_ago", { n: diffMin });
  } else if (diffHours < 24) {
    label = t("hours_ago", { n: diffHours });
  } else {
    label = date.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  return (
    <span
      className="text-[9px] text-muted/50 font-mono"
      title={date.toLocaleString()}
    >
      {t("updated_label")}: {label}
    </span>
  );
}
