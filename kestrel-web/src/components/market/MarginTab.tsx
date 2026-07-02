"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { useTradingDate } from "@/hooks/useTradingDate";

interface MarginRow { date: string; name: string; TodayBalance?: number; }
interface MaintenanceRow { date: string; TotalExchangeMarginMaintenance?: number; }

export function MarginTab() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const monthAgo = daysAgo(30);
  const today = useTradingDate();
  const { data: margin, loading: mL } = useMarketData<MarginRow>("/institutional/margin/total", { start_date: monthAgo, end_date: today });
  const { data: maintenance, loading: mtL } = useMarketData<MaintenanceRow>("/institutional/margin-maintenance", { start_date: monthAgo, end_date: today });

  if (mL || mtL) return <div className="card-atmospheric p-5 h-[450px] animate-shimmer" />;
  const latestMaint = maintenance[maintenance.length - 1];
  const maintRatio = latestMaint?.TotalExchangeMarginMaintenance;

  const marginByDate = new Map<string, { financing: number; shortSelling: number }>();
  for (const r of margin) {
    const e = marginByDate.get(r.date) || { financing: 0, shortSelling: 0 };
    if (r.name.includes("融資") || r.name === "MarginPurchaseMoney") e.financing = r.TodayBalance || 0;
    if (r.name.includes("融券") || r.name === "ShortSale") e.shortSelling = r.TodayBalance || 0;
    marginByDate.set(r.date, e);
  }
  const allDates = Array.from(marginByDate.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  const chartDates = allDates.slice(-20);
  const tableDates = [...allDates].reverse().slice(0, 10);

  // Line chart data
  const finVals = chartDates.map(([, v]) => v.financing / 1e8);
  const shortVals = chartDates.map(([, v]) => v.shortSelling / 1e4);
  const finMin = Math.min(...finVals);
  const finMax = Math.max(...finVals);
  const finRange = finMax - finMin || 1;
  const shortMin = Math.min(...shortVals);
  const shortMax = Math.max(...shortVals);
  const shortRange = shortMax - shortMin || 1;

  const W = 200;
  const H = 60;

  const toPoints = (vals: number[], min: number, range: number) =>
    vals.map((v, i) => `${(i / (vals.length - 1)) * W},${H - 4 - ((v - min) / range) * (H - 8)}`).join(" ");

  const finLine = chartDates.length > 1 ? toPoints(finVals, finMin, finRange) : "";
  const shortLine = chartDates.length > 1 ? toPoints(shortVals, shortMin, shortRange) : "";

  // Daily changes
  const withChange = tableDates.map(([date, val], i) => {
    const prev = i < tableDates.length - 1 ? tableDates[i + 1][1] : null;
    return {
      date,
      financing: val.financing,
      shortSelling: val.shortSelling,
      finChange: prev ? val.financing - prev.financing : 0,
      shortChange: prev ? val.shortSelling - prev.shortSelling : 0,
    };
  });

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{t("margin_change")}</span>
        {maintRatio && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-muted">{t("maintenance_ratio")}</span>
            <span className={`text-xs font-mono font-bold ${maintRatio < 140 ? "text-down" : maintRatio < 160 ? "text-signal" : "text-up"}`}>
              {maintRatio.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Dual line chart: 融資 vs 融券 */}
      {chartDates.length > 1 && (
        <div className="px-4 pt-4 pb-2">
          <div className="flex items-center gap-4 mb-2">
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-3 h-0.5 bg-up inline-block rounded" />{t("margin_balance")}</span>
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-3 h-0.5 bg-signal inline-block rounded" />{t("short_balance")}</span>
          </div>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[60px]" preserveAspectRatio="none">
            <polyline points={finLine} fill="none" stroke="var(--up)" strokeWidth="1.5" strokeLinecap="round" />
            <polyline points={shortLine} fill="none" stroke="var(--signal)" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="3 2" />
          </svg>
          <div className="flex justify-between text-[9px] font-mono text-muted/50 mt-1">
            <span>{chartDates[0]?.[0]?.slice(5)}</span>
            <span>{tm("margin_fin")}: {finVals[finVals.length - 1]?.toFixed(0)}{t("unit_yi")} / {tm("margin_short")}: {shortVals[shortVals.length - 1]?.toFixed(0)}{t("unit_wan_lot")}</span>
            <span>{chartDates[chartDates.length - 1]?.[0]?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* Table */}
      <table className="w-full text-xs">
        <thead>
          <tr className="border-y border-border/30 bg-raised/30">
            <th className="px-4 py-2 text-left text-muted font-medium">{t("date")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("margin_balance")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("change")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("short_balance")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{t("change")}</th>
          </tr>
        </thead>
        <tbody>
          {withChange.map((row) => (
            <tr key={row.date} className="border-b border-border/20 hover:bg-raised/20">
              <td className="px-4 py-2.5 font-mono text-muted">{row.date.slice(5)}</td>
              <td className="px-4 py-2.5 text-right font-mono">
                {row.financing ? `${(row.financing / 1e8).toFixed(1)} ${t("unit_yi")}` : "—"}
              </td>
              <td className={`px-4 py-2.5 text-right font-mono font-medium ${row.finChange >= 0 ? "text-up" : "text-down"}`}>
                {row.finChange !== 0 ? `${row.finChange >= 0 ? "+" : ""}${(row.finChange / 1e8).toFixed(2)}` : "—"}
              </td>
              <td className="px-4 py-2.5 text-right font-mono">
                {row.shortSelling ? `${(row.shortSelling / 1e4).toFixed(1)} ${t("unit_wan_lot")}` : "—"}
              </td>
              <td className={`px-4 py-2.5 text-right font-mono font-medium ${row.shortChange >= 0 ? "text-up" : "text-down"}`}>
                {row.shortChange !== 0 ? `${row.shortChange >= 0 ? "+" : ""}${(row.shortChange / 1e4).toFixed(2)}` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
