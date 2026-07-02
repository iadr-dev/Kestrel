"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { useTradingDate } from "@/hooks/useTradingDate";
import { NetBarsChart } from "./charts/NetBarsChart";
import type { InstRow } from "@/types";

export function InstitutionalFlow() {
  const t = useTranslations("data");
  // ~40 calendar days spans 20+ trading days for the 20-day history chart.
  const monthAgo = daysAgo(40);
  const today = useTradingDate();
  const { data, loading } = useMarketData<InstRow>("/institutional/buy-sell/total", { start_date: monthAgo, end_date: today });

  if (loading || !data.length) return (
    <div className="card-atmospheric p-5 h-[300px]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold">{t("institutional_summary")}</span>
        <span className="text-[10px] text-muted/60">{t("last_5_days")}</span>
      </div>
      <div className="h-[220px] animate-shimmer rounded" />
    </div>
  );

  // Group by date
  const byDate = new Map<string, { foreign: number; trust: number; dealer: number }>();
  for (const r of data) {
    const e = byDate.get(r.date) || { foreign: 0, trust: 0, dealer: 0 };
    const net = (r.buy - r.sell) / 100000000;
    if (r.name.includes("Foreign_Investor") || r.name.includes("外資")) e.foreign = net;
    else if (r.name.includes("Investment_Trust") || r.name.includes("投信")) e.trust = net;
    else if (r.name.includes("Dealer") || r.name.includes("自營")) e.dealer += net;
    byDate.set(r.date, e);
  }

  const allDates = Array.from(byDate.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const latest = allDates[allDates.length - 1];
  const last5 = allDates.slice(-5);
  const last20 = allDates.slice(-20);

  if (!latest) return (
    <div className="card-atmospheric p-5 h-[300px]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold">{t("institutional_summary")}</span>
      </div>
      <div className="h-[220px] animate-shimmer rounded" />
    </div>
  );

  const [, todayVals] = latest;
  const items = [
    { label: t("foreign"), net: todayVals.foreign },
    { label: t("trust"), net: todayVals.trust },
    { label: t("dealer"), net: todayVals.dealer },
  ];
  const maxAbs = Math.max(...items.map((i) => Math.abs(i.net)), 1);

  return (
    <div className="card-atmospheric p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{t("institutional_summary")}</span>
        <span className="text-[10px] text-muted/60">{latest[0]}</span>
      </div>

      {/* Today's bars */}
      <div className="space-y-3 mb-5">
        {items.map((item) => {
          const isUp = item.net >= 0;
          const width = Math.min((Math.abs(item.net) / maxAbs) * 100, 100);
          return (
            <div key={item.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted">{item.label}</span>
                <span className={`text-sm font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{item.net.toFixed(1)} {t("billion")}
                </span>
              </div>
              <div className="h-2 bg-raised rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${isUp ? "bg-up" : "bg-down"}`}
                  style={{ width: `${width}%`, marginLeft: isUp ? "0" : "auto", marginRight: isUp ? "auto" : "0" }}
                />
              </div>
            </div>
          );
        })}
        <div className="pt-2 border-t border-border/30 flex items-center justify-between">
          <span className="text-xs text-muted">{t("total")}</span>
          <span className={`text-sm font-mono font-bold ${items.reduce((a, b) => a + b.net, 0) >= 0 ? "text-up" : "text-down"}`}>
            {items.reduce((a, b) => a + b.net, 0) >= 0 ? "+" : ""}{items.reduce((a, b) => a + b.net, 0).toFixed(1)} {t("billion")}
          </span>
        </div>
      </div>

      {/* Grouped bar history: last 5 days + last 20 days. The 20-day chart flex-fills
          so the pair always reaches the bottom of the (grid-stretched) card. */}
      <div className="pt-4 border-t border-border/30 space-y-5 flex flex-col flex-1 min-h-0">
        <NetBarsChart
          title={t("last_5_days")}
          dates={last5.map(([d]) => d)}
          series={INST_SERIES}
          values={last5.map(([, v]) => [v.foreign, v.trust, v.dealer])}
          height={110}
          unit={t("billion")}
          fmt={(v) => v.toFixed(0)}
          xLabels="weekday"
        />
        <NetBarsChart
          title={t("last_20_days")}
          dates={last20.map(([d]) => d)}
          series={INST_SERIES}
          values={last20.map(([, v]) => [v.foreign, v.trust, v.dealer])}
          fill
          unit={t("billion")}
          fmt={(v) => v.toFixed(0)}
          xLabels="endpoints"
        />
        <div className="flex gap-4 justify-center">
          <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-down" />{t("foreign")}</span>
          <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-signal" />{t("trust")}</span>
          <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-400" />{t("dealer")}</span>
        </div>
      </div>
    </div>
  );
}

// Series colors for the 外資 / 投信 / 自營 grouped net bars.
const INST_SERIES = [
  { color: "bg-down" },
  { color: "bg-signal" },
  { color: "bg-blue-400" },
];
