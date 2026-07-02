"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";

interface SectorMove {
  stock_id?: string;
  sector_name?: string;
  // Endpoint returns `change` (sector index point change), not `change_pct`.
  change?: number;
}

export function IntradayMovers() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const today = useTradingDate();

  const { data, loading } = useMarketData<SectorMove>("/market/indices/sector-change", {
    start_date: today,
    end_date: today,
  });

  const sorted = loading ? [] : [...data]
    .filter((s) => s.change !== undefined && s.sector_name)
    .sort((a, b) => Math.abs(b.change || 0) - Math.abs(a.change || 0))
    .slice(0, 10);

  if (loading || sorted.length === 0) {
    return (
      <div className="card-atmospheric overflow-hidden h-[300px]">
        <div className="px-5 py-3 border-b border-border/30">
          <span className="text-sm font-semibold">{tm("intraday_movers_title")}</span>
        </div>
        <div className="flex-1 flex items-center justify-center h-[240px] text-sm text-muted">
          {loading ? <div className="h-[210px] w-full mx-5 animate-shimmer rounded" /> : t("no_data_non_trading")}
        </div>
      </div>
    );
  }

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-5 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("intraday_movers_title")}</span>
      </div>

      {/* Header */}
      <div className="flex items-center px-5 py-2 text-[10px] text-muted border-b border-border/20">
        <span className="w-6">#</span>
        <span className="flex-1">{tm("sector_label")}</span>
        <span className="w-24 text-right">{tm("index_points")}</span>
      </div>

      <div className="divide-y divide-border/10">
        {sorted.map((s, i) => {
          const change = s.change || 0;
          const isUp = change >= 0;

          return (
            <div
              key={`${s.sector_name}-${i}`}
              className="flex items-center px-5 py-2.5 hover:bg-raised/30 transition-colors"
            >
              <span className="w-6 text-[10px] font-mono text-muted/70">{i + 1}</span>

              <span className="flex-1 text-xs font-medium truncate">
                {s.sector_name}
              </span>

              <span className={`w-24 text-right text-xs font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                {isUp ? "▲" : "▼"}{Math.abs(change).toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
