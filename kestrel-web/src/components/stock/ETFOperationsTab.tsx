"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface Op {
  stock_name: string;
  action: "新增" | "刪除" | "加碼" | "減碼";
  shares_delta?: number | null;
  weight_pct?: number | null;
}
interface OpsData {
  latest: string | null;
  prior: string | null;
  ops: Op[];
}

const ACTION_STYLE: Record<Op["action"], string> = {
  新增: "bg-up/15 text-up",
  加碼: "bg-up/15 text-up",
  刪除: "bg-down/15 text-down",
  減碼: "bg-down/15 text-down",
};

/** 操作日報 — an active ETF's holdings changes (加碼/減碼/新增/刪除) between its two most
 *  recent daily snapshots. Snapshots accumulate nightly server-side, so this is empty
 *  until ≥2 sessions have been collected (shows an explanatory note meanwhile). */
export function ETFOperationsTab({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.etf.operations(stockId),
    queryFn: () =>
      apiFetch<{ data: OpsData | null }>(`/etf/${encodeURIComponent(stockId)}/operations`)
        .then((r) => r.data)
        .catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-40 animate-shimmer rounded-2xl" />;

  const ops = data?.ops ?? [];

  if (ops.length === 0) {
    return (
      <div className="card-atmospheric p-4">
        <h4 className="text-xs font-semibold mb-2">{t("etf_operations")}</h4>
        <p className="text-xs text-muted text-center py-4">{t("etf_operations_pending")}</p>
      </div>
    );
  }

  return (
    <div className="card-atmospheric p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold">{t("etf_operations")}</h4>
        {data?.latest && <span className="text-[10px] text-muted font-mono">{data.latest}</span>}
      </div>
      <div className="space-y-1.5">
        {ops.map((o) => (
          <div key={o.stock_name} className="flex items-center gap-3 text-xs border-b border-border/10 pb-1.5">
            <span className={`shrink-0 w-10 text-center text-[10px] font-semibold rounded-md px-1 py-0.5 ${ACTION_STYLE[o.action]}`}>
              {o.action}
            </span>
            <span className="flex-1 truncate text-foreground/80">{o.stock_name}</span>
            {o.shares_delta != null && (
              <span className={`font-mono ${o.shares_delta >= 0 ? "text-up" : "text-down"}`}>
                {o.shares_delta >= 0 ? "+" : ""}
                {o.shares_delta.toLocaleString()} {t("active_etf_lots")}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
