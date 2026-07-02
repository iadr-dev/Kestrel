"use client";

import { useTranslations } from "next-intl";
import { fmtLargeNumber } from "@/lib/format";

interface Holder {
  etf_id: string;
  etf_name?: string;
  weight_pct?: number | null;
  shares_lots?: number | null;
  est_value?: number | null;
}
interface Props {
  data: {
    stock_id: string;
    total_est_value?: number | null;
    holders: Holder[];
  };
}

/** 持有主動式ETF rich card — which active ETFs hold a stock, with weight/張數/市值. */
export function ActiveEtfHoldersCard({ data }: Props) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const units = { yi: td("unit_yi"), wan: td("unit_wan") };
  const holders = data.holders ?? [];
  if (holders.length === 0) return null;

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-bold flex items-center gap-1.5">
          <span className="font-mono">{data.stock_id}</span>
          {t("active_etf_title")}
        </span>
        <span className="text-[10px] text-muted">
          {holders.length} {t("active_etf_count_unit")}
          {data.total_est_value != null ? ` · ${fmtLargeNumber(data.total_est_value, units)}` : ""}
        </span>
      </div>
      <div className="space-y-1.5">
        {holders.map((h) => (
          <div key={h.etf_id} className="flex items-center gap-2 text-xs border-b border-border/10 pb-1.5">
            <span className="font-mono font-semibold shrink-0">{h.etf_id}</span>
            <span className="flex-1 truncate text-foreground/80">{h.etf_name}</span>
            {h.shares_lots != null && <span className="text-[10px] text-muted">{h.shares_lots.toLocaleString()} {t("active_etf_lots")}</span>}
            <span className="font-mono text-right w-14">
              {h.est_value != null ? fmtLargeNumber(h.est_value, units) : h.weight_pct != null ? `${h.weight_pct.toFixed(2)}%` : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
