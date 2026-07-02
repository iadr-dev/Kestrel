"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate, isTwMarketOpen } from "@/hooks/useTradingDate";

interface SectorChange {
  stock_id: string;
  change: number;
  sector_name?: string;
  volume?: number;
}

export function SectorRotation() {
  const tm = useTranslations("market");
  const td = useTranslations("data");
  const locale = useLocale();
  const today = useTradingDate();
  const [seeAll, setSeeAll] = useState(false);
  const weekAgo = (() => { const d = new Date(today); d.setDate(d.getDate() - 7); return d.toISOString().split("T")[0]; })();

  // 資金流向 is intraday-live: the backend computes it from the 5-second sector index.
  // Poll every 60s while the TWSE session is open so the rotation refreshes during the
  // day; when closed the endpoint walks back to the last session (never empty).
  const marketOpen = isTwMarketOpen();
  const { data, loading } = useMarketData<SectorChange>(
    "/market/indices/sector-change",
    { start_date: weekAgo, end_date: today, locale },
    marketOpen ? { staleTime: 30_000, refetchInterval: 60_000 } : undefined,
  );

  if (loading || !data.length) return (
    <div className="card-atmospheric p-5 h-[200px]">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{tm("sector_rotation_title")}</span>
        <span className="text-[10px] text-muted/60">{tm("weekly")}</span>
      </div>
      {loading ? (
        <div className="h-[120px] animate-shimmer rounded" />
      ) : (
        <div className="h-[120px] flex items-center justify-center text-sm text-muted">{td("no_data_non_trading")}</div>
      )}
    </div>
  );

  const sorted = [...data].sort((a, b) => b.change - a.change);
  const cap = seeAll ? undefined : 5;
  const inflow = sorted.filter((s) => s.change > 0).slice(0, cap);
  const outflow = sorted.filter((s) => s.change < 0).reverse().slice(0, cap);

  const maxAbs = Math.max(
    ...inflow.map((s) => Math.abs(s.change)),
    ...outflow.map((s) => Math.abs(s.change)),
    0.1
  );

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{tm("sector_rotation_title")}</span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-muted/60">{tm("weekly")}</span>
          <button onClick={() => setSeeAll((v) => !v)} className="text-[10px] text-signal hover:underline">
            {seeAll ? tm("collapse") : `${tm("see_all")} ›`}
          </button>
        </div>
      </div>

      <div className={`grid grid-cols-1 lg:grid-cols-2 gap-4 ${seeAll ? "max-h-[420px] overflow-y-auto" : ""}`}>
        {/* Inflow */}
        <div>
          <span className="text-[10px] text-up font-medium mb-2 block">{tm("inflow")}</span>
          <div className="space-y-1.5">
            {inflow.map((s) => {
              const width = (Math.abs(s.change) / maxAbs) * 100;
              return (
                <div key={s.stock_id} className="flex items-center gap-2">
                  <span className="text-[10px] text-foreground/70 w-24 truncate">{s.sector_name || s.stock_id}</span>
                  <div className="flex-1 h-3 bg-raised rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-up/70" style={{ width: `${width}%` }} />
                  </div>
                  <span className="text-[10px] font-mono text-up font-bold w-14 text-right">+{s.change.toFixed(2)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Outflow */}
        <div>
          <span className="text-[10px] text-down font-medium mb-2 block">{tm("outflow")}</span>
          <div className="space-y-1.5">
            {outflow.map((s) => {
              const width = (Math.abs(s.change) / maxAbs) * 100;
              return (
                <div key={s.stock_id} className="flex items-center gap-2">
                  <span className="text-[10px] text-foreground/70 w-24 truncate">{s.sector_name || s.stock_id}</span>
                  <div className="flex-1 h-3 bg-raised rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-down/70" style={{ width: `${width}%` }} />
                  </div>
                  <span className="text-[10px] font-mono text-down font-bold w-14 text-right">{s.change.toFixed(2)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
