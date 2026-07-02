"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";
import { daysAgo } from "@/lib/date";
import { NetBarsChart } from "./charts/NetBarsChart";
import { ChartFrame } from "./charts/ChartFrame";
import type { InstRow, FuturesRow } from "@/types";

interface MarginTotal { date: string; name: string; TodayBalance?: number; }

export function ChipDaily() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const weekAgo = daysAgo(7);
  const today = useTradingDate();

  const { data: instData, loading: instL } = useMarketData<InstRow>("/institutional/buy-sell/total", { start_date: weekAgo, end_date: today });
  const { data: marginData, loading: marginL } = useMarketData<MarginTotal>("/institutional/margin/total", { start_date: weekAgo, end_date: today });
  const { data: futuresData, loading: futL } = useMarketData<FuturesRow>("/derivatives/futures/institutional", { data_id: "TX", start_date: weekAgo, end_date: today });

  const loading = instL || marginL || futL;

  if (loading || instData.length === 0) return (
    <div className="card-atmospheric overflow-hidden h-[320px]">
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{tm("chip_daily_title")}</span>
      </div>
      <div className="h-[260px] animate-shimmer rounded m-4" />
    </div>
  );

  // Latest date
  const latestDate = instData[instData.length - 1].date;

  // Per-day 三大法人 net buy (億) over the fetched window → trend bars below the
  // metric grid (fills the previously-empty lower half of the card).
  const dates = Array.from(new Set(instData.map((r) => r.date))).sort();
  const dailyNet = dates.map((d) => {
    const rows = instData.filter((r) => r.date === d);
    const net = rows.reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;
    return { date: d, net };
  });

  // Per-day total margin balance (融資, 億) trend line.
  const marginDates = Array.from(new Set(marginData.map((r) => r.date))).sort();
  const marginSeries = marginDates.map((d) => {
    const rows = marginData.filter((r) => r.date === d && (r.name.includes("融資") || r.name === "MarginPurchaseMoney"));
    return { date: d, bal: rows.reduce((sum, r) => sum + (r.TodayBalance || 0), 0) / 1e8 };
  });
  const marginMin = Math.min(...marginSeries.map((m) => m.bal));
  const marginMax = Math.max(...marginSeries.map((m) => m.bal));
  const marginRange = marginMax - marginMin || 1;

  // Institutional net
  const latestInst = instData.filter((r) => r.date === latestDate);
  const foreignNet = latestInst
    .filter((r) => r.name.includes("Foreign") || r.name.includes("外資"))
    .reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;
  const trustNet = latestInst
    .filter((r) => r.name.includes("Investment_Trust") || r.name.includes("投信"))
    .reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;
  const dealerNet = latestInst
    .filter((r) => r.name.includes("Dealer") || r.name.includes("自營"))
    .reduce((sum, r) => sum + (r.buy - r.sell), 0) / 1e8;
  const totalNet = foreignNet + trustNet + dealerNet;

  // Margin
  const latestMargin = marginData.filter((r) => r.date === marginData[marginData.length - 1]?.date);
  const marginChange = latestMargin
    .filter((r) => r.name.includes("融資") || r.name === "MarginPurchaseMoney")
    .reduce((sum, r) => sum + (r.TodayBalance || 0), 0);
  const shortChange = latestMargin
    .filter((r) => r.name.includes("融券") || r.name === "ShortSale")
    .reduce((sum, r) => sum + (r.TodayBalance || 0), 0);

  // Futures OI
  const latestFutDate = futuresData.length > 0 ? futuresData[futuresData.length - 1].date : null;
  const foreignOI = latestFutDate
    ? futuresData.filter((r) => r.date === latestFutDate && ((r.institutional_investors || r.name || "").includes("Foreign") || (r.institutional_investors || r.name || "").includes("外資")))
      .reduce((sum, r) => sum + ((r.long_open_interest_balance_volume || 0) - (r.short_open_interest_balance_volume || 0)), 0)
    : 0;

  const metrics = [
    { label: tm("chip_total_3inst"), value: totalNet, unit: t("unit_yi"), fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}` },
    { label: t("foreign"), value: foreignNet, unit: t("unit_yi"), fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}` },
    { label: t("trust"), value: trustNet, unit: t("unit_yi"), fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}` },
    { label: t("dealer"), value: dealerNet, unit: t("unit_yi"), fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}` },
    { label: tm("foreign_oi"), value: foreignOI, unit: t("unit_contract"), fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toLocaleString()}` },
    { label: t("margin_balance"), value: marginChange / 1e8, unit: t("unit_yi"), fmt: (v: number) => `${(v).toFixed(1)}` },
    { label: t("short_balance"), value: shortChange / 1e4, unit: t("unit_wan_lot"), fmt: (v: number) => `${(v).toFixed(1)}` },
  ];

  return (
    <div className="card-atmospheric overflow-hidden flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{tm("chip_daily_title")}</span>
        <span className="text-[10px] text-muted/60">{latestDate}</span>
      </div>

      {/* Key metrics grid */}
      <div className="p-4 grid grid-cols-2 gap-2">
        {metrics.map((m) => {
          const isUp = m.value >= 0;
          return (
            <div key={m.label} className="border border-border/30 rounded-lg px-3 py-2">
              <div className="text-[10px] text-muted truncate">{m.label}</div>
              <div className={`text-sm font-mono font-bold mt-0.5 ${isUp ? "text-up" : "text-down"}`}>
                {m.fmt(m.value)} <span className="text-[9px] text-muted font-normal">{m.unit}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 三大法人 net-buy trend (daily, 億) — shared net-bar chart, fills the card's
          stretched height so the lower half isn't blank. */}
      {dailyNet.length > 1 && (
        <div className="px-4 pb-4 flex flex-col flex-1 min-h-0">
          <NetBarsChart
            title={`${tm("chip_total_3inst")} · ${t("net")} (${t("unit_yi")})`}
            dates={dailyNet.map((d) => d.date)}
            series={[{ color: "bg-up" }]}
            values={dailyNet.map((d) => [d.net])}
            fill
            unit={t("unit_yi")}
            fmt={(v) => v.toFixed(0)}
            xLabels="endpoints"
            barMaxWidth={11}
          />
        </div>
      )}

      {/* 融資餘額 trend line (億) — shared frame with gridlines + min/max axis */}
      {marginSeries.length > 1 && (
        <div className="px-4 pb-4">
          <span className="text-[10px] text-muted/60 mb-1.5 block">{t("margin_balance")} ({t("unit_yi")})</span>
          <ChartFrame height={60} yMax={marginMax} yMin={marginMin} fmt={(v) => v.toFixed(0)} dates={marginSeries.map((m) => m.date)} xLabels="endpoints">
            <svg viewBox="0 0 200 60" preserveAspectRatio="none" className="absolute inset-0 w-full h-full">
              <polyline
                points={marginSeries.map((m, i) => {
                  const x = (i / (marginSeries.length - 1)) * 200;
                  const y = 58 - ((m.bal - marginMin) / marginRange) * 56;
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                }).join(" ")}
                fill="none"
                stroke="var(--signal)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          </ChartFrame>
        </div>
      )}

      {/* Summary bar */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted">{tm("chip_total_3inst")}:</span>
          <span className={`font-mono font-bold ${totalNet >= 0 ? "text-up" : "text-down"}`}>
            {totalNet >= 0 ? "+" : ""}{totalNet.toFixed(1)} {t("unit_yi")}
          </span>
          <span className="text-muted/40">|</span>
          <span className="text-muted">{tm("foreign_oi")}:</span>
          <span className={`font-mono font-bold ${foreignOI >= 0 ? "text-up" : "text-down"}`}>
            {foreignOI >= 0 ? "+" : ""}{foreignOI.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
