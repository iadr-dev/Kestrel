"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";

interface SectorIndex {
  date: string;
  stock_id: string;
  price: number;
  sector_name?: string;
}

function getSectorColor(change: number): string {
  const abs = Math.abs(change);
  const intensity = Math.min(abs / 3, 1);
  if (change >= 0) {
    return `rgba(255,95,74,${0.08 + intensity * 0.42})`;
  }
  return `rgba(94,232,133,${0.08 + intensity * 0.42})`;
}

export function SectorGrid() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const locale = useLocale();
  const today = useTradingDate();
  const [showAll, setShowAll] = useState(false);

  const { data, loading } = useMarketData<SectorIndex>("/market/indices/5sec", {
    trade_date: today,
    locale,
  });

  if (loading || !data.length) return (
    <div className="card-atmospheric p-5 h-[280px]">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{t("sector_realtime")}</span>
        <button className="text-[10px] text-signal hover:underline">{tm("see_all")} ›</button>
      </div>
      <div className="h-[200px] animate-shimmer rounded" />
    </div>
  );

  // Compute sector changes
  const sectorData = new Map<string, { first: number; last: number; count: number }>();
  for (const r of data) {
    const e = sectorData.get(r.stock_id);
    if (!e) sectorData.set(r.stock_id, { first: r.price, last: r.price, count: 1 });
    else { e.last = r.price; e.count++; }
  }

  const sectors = Array.from(sectorData.entries())
    .map(([id, { first, last, count }]) => ({
      id,
      change: first > 0 ? ((last - first) / first) * 100 : 0,
      weight: count,
    }))
    .sort((a, b) => b.change - a.change);

  const nameMap = new Map<string, string>();
  for (const r of data) {
    if (r.sector_name && !nameMap.has(r.stock_id)) nameMap.set(r.stock_id, r.sector_name);
  }
  const getName = (id: string) => nameMap.get(id) || id;

  // Treemap-like sizing: scale by relative weight
  const maxWeight = Math.max(...sectors.map((s) => s.weight), 1);
  const getSpan = (weight: number) => {
    const ratio = weight / maxWeight;
    if (ratio > 0.6) return "col-span-2 row-span-2";
    if (ratio > 0.3) return "col-span-2";
    return "";
  };

  const displayed = showAll ? sectors : sectors.slice(0, 16);

  return (
    <>
      <div className="card-atmospheric p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-semibold">{t("sector_realtime")}</span>
          <button
            onClick={() => setShowAll(true)}
            className="text-[10px] text-signal hover:underline"
          >
            {tm("see_all")} ›
          </button>
        </div>
        <div className="grid grid-cols-4 auto-rows-[60px] gap-1.5">
          {displayed.slice(0, 16).map((s) => {
            const isUp = s.change >= 0;
            return (
              <div
                key={s.id}
                className={`px-2 py-2 rounded-xl text-center transition-all hover:scale-[1.02] hover:shadow-sm flex flex-col items-center justify-center ${getSpan(s.weight)}`}
                style={{ backgroundColor: getSectorColor(s.change) }}
              >
                <div className="text-[10px] font-medium text-foreground/80 truncate w-full">
                  {getName(s.id)}
                </div>
                <div className={`text-xs font-mono font-bold mt-0.5 ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{s.change.toFixed(2)}%
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 mt-3 justify-center">
          <span className="text-[9px] text-muted flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: getSectorColor(5) }} />
            {tm("limit_up")}
          </span>
          <span className="text-[9px] text-muted flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: getSectorColor(2) }} />
            &gt;+1%
          </span>
          <span className="text-[9px] text-muted flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: getSectorColor(0.2) }} />
            {tm("flat_label")}
          </span>
          <span className="text-[9px] text-muted flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: getSectorColor(-2) }} />
            &gt;-1%
          </span>
          <span className="text-[9px] text-muted flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ backgroundColor: getSectorColor(-5) }} />
            {tm("limit_down")}
          </span>
        </div>
      </div>

      {/* Full-screen modal */}
      {showAll && (
        <div className="fixed inset-0 z-50 bg-background/95 backdrop-blur-sm overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold">{t("sector_realtime")}</h2>
              <button
                onClick={() => setShowAll(false)}
                className="px-3 py-1.5 text-sm rounded-lg border border-border/40 hover:bg-raised transition-colors"
              >
                ✕ {tm("close")}
              </button>
            </div>
            <div className="grid grid-cols-4 md:grid-cols-6 auto-rows-[70px] gap-2">
              {sectors.map((s) => {
                const isUp = s.change >= 0;
                return (
                  <div
                    key={s.id}
                    className={`px-3 py-2 rounded-xl text-center flex flex-col items-center justify-center ${getSpan(s.weight)}`}
                    style={{ backgroundColor: getSectorColor(s.change) }}
                  >
                    <div className="text-xs font-medium text-foreground/80 truncate w-full">
                      {getName(s.id)}
                    </div>
                    <div className={`text-sm font-mono font-bold mt-0.5 ${isUp ? "text-up" : "text-down"}`}>
                      {isUp ? "+" : ""}{s.change.toFixed(2)}%
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
