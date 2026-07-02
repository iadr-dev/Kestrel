"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { logError } from "@/lib/log";

/** Route-level error boundary for the dashboard. Next.js renders this when a
 *  dashboard page throws during render, keeping the sidebar/layout intact and
 *  offering a retry instead of a blank screen. */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("common");

  useEffect(() => {
    logError("dashboard.route", error);
  }, [error]);

  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 p-8 text-center">
      <p className="text-sm text-muted max-w-sm">{t("error")}</p>
      <button
        onClick={reset}
        className="px-4 py-2 text-xs font-medium rounded-xl bg-signal/15 text-signal border border-signal/30 hover:bg-signal/25 transition-colors"
      >
        {t("retry")}
      </button>
    </div>
  );
}
