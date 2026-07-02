"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { fmtLargeNumber } from "@/lib/format";

interface Holder {
  etf_id: string;
  etf_name?: string;
  weight_pct?: number | null;
  shares_lots?: number | null;
  est_value?: number | null;
}
interface ActiveHolders {
  stock_id: string;
  holders: Holder[];
  count: number;
  total_est_value?: number | null;
  active_etf_universe?: number;
}

/** 持有主動式ETF — which 主動式ETF (active ETFs) hold this stock, with 持股市值 (AUM-derived)
 *  and 佔個股比重. Inverts the active-ETF universe's full holdings server-side. Renders
 *  nothing when no active ETF holds the stock (common for small/micro caps). TW-only. */
export function ActiveEtfHoldersCard({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const router = useRouter();
  const units = { yi: td("unit_yi"), wan: td("unit_wan") };

  const { data } = useQuery({
    queryKey: queryKeys.etf.activeHolders(stockId),
    queryFn: () =>
      apiFetch<{ data: ActiveHolders | null }>(`/etf/active-holders/${encodeURIComponent(stockId)}`)
        .then((r) => r.data)
        .catch(() => null),
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (!data || data.count === 0) return null;

  return (
    <div className="card-atmospheric p-4">
      <h4 className="text-xs font-semibold mb-3">{t("active_etf_title")}</h4>

      {/* Aggregate header */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-3">
        <Stat label={t("active_etf_count")} value={`${data.count} ${t("active_etf_count_unit")}`} />
        {data.total_est_value != null && (
          <Stat label={t("active_etf_total_value")} value={fmtLargeNumber(data.total_est_value, units)} />
        )}
      </div>

      {/* Per-ETF rows */}
      <div className="space-y-1.5">
        {data.holders.map((h) => (
          <button
            key={h.etf_id}
            onClick={() => router.push(`/dashboard/stocks/${h.etf_id}?at=etf`)}
            className="w-full flex items-center gap-3 text-left rounded-lg px-2 py-1.5 hover:bg-raised/60 transition-colors"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-xs font-semibold">{h.etf_id}</span>
                <span className="text-xs text-foreground/80 truncate">{h.etf_name}</span>
              </div>
              {h.shares_lots != null && (
                <div className="text-[10px] text-muted">
                  {h.shares_lots.toLocaleString()} {t("active_etf_lots")}
                </div>
              )}
            </div>
            <div className="shrink-0 text-right">
              {h.est_value != null && (
                <div className="text-xs font-mono font-medium">{fmtLargeNumber(h.est_value, units)}</div>
              )}
              {h.weight_pct != null && (
                <div className="text-[10px] text-muted font-mono">{h.weight_pct.toFixed(2)}%</div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-muted">{label}</div>
      <div className="text-sm font-mono font-medium">{value}</div>
    </div>
  );
}
