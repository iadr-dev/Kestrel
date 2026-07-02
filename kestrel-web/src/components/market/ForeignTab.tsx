"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { useTradingDate } from "@/hooks/useTradingDate";
import { NetBarsChart } from "./charts/NetBarsChart";
import { ChartFrame } from "./charts/ChartFrame";

interface InstitutionalRow { date: string; name: string; buy: number; sell: number; }
interface FuturesRow {
  date: string;
  institutional_investors?: string;
  name?: string;
  long_open_interest_balance_volume?: number;
  short_open_interest_balance_volume?: number;
}

export function ForeignTab() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const monthAgo = daysAgo(30);
  const today = useTradingDate();

  const { data, loading } = useMarketData<InstitutionalRow>("/institutional/buy-sell/total", { start_date: monthAgo, end_date: today });
  const { data: futures, loading: fL } = useMarketData<FuturesRow>("/derivatives/futures/institutional", { data_id: "TX", start_date: monthAgo, end_date: today });

  if (loading || fL || !data.length) return (
    <div className="card-atmospheric overflow-hidden h-[450px]">
      <div className="px-4 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{t("foreign")}</span>
      </div>
      <div className="h-[380px] animate-shimmer rounded m-4" />
    </div>
  );

  // Foreign buy/sell by date
  const foreign = data.filter((r) => r.name.includes("外資") || r.name.includes("Foreign_Investor") || r.name.includes("Foreign"));
  const byDate = new Map<string, { buy: number; sell: number; net: number }>();
  for (const row of foreign) {
    const e = byDate.get(row.date) || { buy: 0, sell: 0, net: 0 };
    e.buy += row.buy; e.sell += row.sell; e.net = e.buy - e.sell;
    byDate.set(row.date, e);
  }
  const allDates = Array.from(byDate.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const last20 = allDates.slice(-20);
  const tableData = [...allDates].reverse().slice(0, 10);

  // OI data
  const oiByDate = new Map<string, number>();
  for (const r of futures) {
    const inst = r.institutional_investors || r.name || "";
    if (inst.includes("Foreign") || inst.includes("外資")) {
      const net = (r.long_open_interest_balance_volume || 0) - (r.short_open_interest_balance_volume || 0);
      oiByDate.set(r.date, (oiByDate.get(r.date) || 0) + net);
    }
  }
  const oiDates = Array.from(oiByDate.entries()).sort((a, b) => a[0].localeCompare(b[0])).slice(-20);

  // OI line scaling
  const oiVals = oiDates.map(([, v]) => v);
  const oiMin = Math.min(...oiVals);
  const oiMax = Math.max(...oiVals);
  const oiRange = oiMax - oiMin || 1;

  // Cumulative
  const nets = tableData.map(([, v]) => v.net);
  const cum5 = nets.slice(0, 5).reduce((a, b) => a + b, 0);
  const cum10 = nets.reduce((a, b) => a + b, 0);

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-4 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{t("foreign")} · {t("net")}</span>
      </div>

      {/* 20-day net buy bar chart — shared net-bar chart (gridlines + ±max axis) */}
      <div className="px-4 pt-4 pb-2">
        <NetBarsChart
          title={tm("foreign_net_20d")}
          dates={last20.map(([d]) => d)}
          series={[{ color: "bg-up" }]}
          values={last20.map(([, v]) => [v.net / 1e8])}
          height={120}
          unit={t("unit_yi")}
          fmt={(v) => v.toFixed(0)}
          xLabels="endpoints"
          barMaxWidth={8}
        />
      </div>

      {/* OI position line chart — shared frame with gridlines + min/max axis */}
      {oiDates.length > 1 && (
        <div className="px-4 pb-3">
          <span className="text-[10px] text-muted/60 mb-1 block">{tm("oi_position")}</span>
          <ChartFrame height={56} yMax={oiMax} yMin={oiMin} fmt={(v) => v.toLocaleString()} dates={oiDates.map(([d]) => d)} xLabels="endpoints" axisWidth={48}>
            <svg viewBox="0 0 200 56" className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
              <defs>
                <linearGradient id="oi-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--signal)" stopOpacity="0.15" />
                  <stop offset="100%" stopColor="var(--signal)" stopOpacity="0" />
                </linearGradient>
              </defs>
              {(() => {
                const points = oiDates.map(([, v], i) => {
                  const x = (i / (oiDates.length - 1)) * 200;
                  const y = 54 - ((v - oiMin) / oiRange) * 52;
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                });
                const line = points.join(" ");
                const area = `0,56 ${line} 200,56`;
                return (
                  <>
                    <polygon points={area} fill="url(#oi-grad)" />
                    <polyline points={line} fill="none" stroke="var(--signal)" strokeWidth="1.5" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
                  </>
                );
              })()}
            </svg>
          </ChartFrame>
          <div className="text-center text-[9px] font-mono text-muted/50 mt-1">
            {t("oi_net")}: {oiVals[oiVals.length - 1]?.toLocaleString()}
          </div>
        </div>
      )}

      {/* Cumulative summary */}
      <div className="grid grid-cols-2 gap-3 px-4 pb-3">
        <div className="border border-border/40 rounded-xl p-3">
          <div className="text-[10px] text-muted">{t("cum_5d")}</div>
          <div className={`text-lg font-mono font-bold mt-1 ${cum5 >= 0 ? "text-up" : "text-down"}`}>
            {cum5 >= 0 ? "+" : ""}{(cum5 / 1e8).toFixed(1)} {t("unit_yi")}
          </div>
        </div>
        <div className="border border-border/40 rounded-xl p-3">
          <div className="text-[10px] text-muted">{t("cum_10d")}</div>
          <div className={`text-lg font-mono font-bold mt-1 ${cum10 >= 0 ? "text-up" : "text-down"}`}>
            {cum10 >= 0 ? "+" : ""}{(cum10 / 1e8).toFixed(1)} {t("unit_yi")}
          </div>
        </div>
      </div>

      {/* Table */}
      <table className="w-full text-xs">
        <thead>
          <tr className="border-y border-border/30 bg-raised/30">
            <th className="px-4 py-2 text-left text-muted font-medium">{t("date")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("buy")}({t("unit_yi")})</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("sell")}({t("unit_yi")})</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("net")}({t("unit_yi")})</th>
          </tr>
        </thead>
        <tbody>
          {tableData.map(([date, val]) => (
            <tr key={date} className="border-b border-border/20 hover:bg-raised/20">
              <td className="px-4 py-2.5 font-mono text-muted">{date.slice(5)}</td>
              <td className="px-4 py-2.5 text-right font-mono text-up">{(val.buy / 1e8).toFixed(1)}</td>
              <td className="px-4 py-2.5 text-right font-mono text-down">{(val.sell / 1e8).toFixed(1)}</td>
              <td className={`px-4 py-2.5 text-right font-mono font-bold ${val.net >= 0 ? "text-up" : "text-down"}`}>
                {val.net >= 0 ? "+" : ""}{(val.net / 1e8).toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
