"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface HoldingLevel { level: string; people: number; percent: number; shares: number }
interface HoldingDistribution {
  stock_id: string;
  latest_date: string | null;
  levels: HoldingLevel[];
  buckets: { retail?: number; mid?: number; whale?: number };
  whale_pct: number | null;
  total_holders: number;
  trend: { date: string; retail: number; mid: number; whale: number; whale_1000: number }[];
}

/** 大戶資訊 — TDCC 集保 shareholding distribution. Headline 千張大戶 %, retail/mid/whale
 *  buckets, a per-level breakdown, and a weekly concentration trend (是否在集中籌碼). */
export function ShareholdingSection({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.institutional.holdingDistribution(stockId),
    queryFn: () => apiFetch<{ data: HoldingDistribution }>(`/institutional/holding-distribution/${stockId}`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading) return <div className="h-40 animate-shimmer rounded-2xl" />;
  if (!data || !data.levels.length) return <p className="text-xs text-muted p-4">{t("no_data")}</p>;

  const buckets = [
    { label: t("chip_retail"), value: data.buckets.retail ?? 0, color: "bg-up/60" },
    { label: t("chip_mid"), value: data.buckets.mid ?? 0, color: "bg-legendary/60" },
    { label: t("chip_whale"), value: data.buckets.whale ?? 0, color: "bg-signal/60" },
  ];

  // Concentration delta: latest whale% vs the earliest week in the trend window.
  const trend = data.trend;
  const delta = trend.length >= 2 ? trend[trend.length - 1].whale_1000 - trend[0].whale_1000 : 0;
  const concLabel = Math.abs(delta) < 0.05 ? t("concentration_flat") : delta > 0 ? t("concentration_up") : t("concentration_down");
  const concColor = Math.abs(delta) < 0.05 ? "text-muted" : delta > 0 ? "text-up" : "text-down";
  const maxPeople = Math.max(...data.levels.map(l => l.people), 1);

  return (
    <div className="space-y-4">
      {/* Headline: 千張大戶 + total holders + concentration */}
      <div className="grid grid-cols-3 gap-2">
        <div className="card-atmospheric p-3">
          <div className="text-[10px] text-muted mb-1">{t("whale_1000_title")}</div>
          <div className="text-lg font-bold font-mono text-signal">{data.whale_pct != null ? `${data.whale_pct.toFixed(2)}%` : "—"}</div>
        </div>
        <div className="card-atmospheric p-3">
          <div className="text-[10px] text-muted mb-1">{t("total_holders")}</div>
          <div className="text-lg font-bold font-mono">{data.total_holders.toLocaleString()}</div>
        </div>
        <div className="card-atmospheric p-3">
          <div className="text-[10px] text-muted mb-1">{t("concentration_trend")}</div>
          <div className={`text-sm font-bold ${concColor}`}>{concLabel}<span className="text-[10px] font-mono ml-1">{delta >= 0 ? "+" : ""}{delta.toFixed(2)}%</span></div>
        </div>
      </div>

      {/* Retail / mid / whale buckets */}
      <div className="card-atmospheric p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-xs font-semibold">{t("chip_distribution")}</h4>
          {data.latest_date && <span className="text-[10px] text-muted">{t("as_of", { date: data.latest_date })}</span>}
        </div>
        <div className="space-y-3">
          {buckets.map(({ label, value, color }) => (
            <div key={label}>
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-muted">{label}</span>
                <span className="font-mono font-medium">{value.toFixed(2)}%</span>
              </div>
              <div className="h-2 bg-raised rounded-full overflow-hidden">
                <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${Math.min(value, 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Concentration trend mini-bars (whale_1000 over weeks) */}
      {trend.length >= 2 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-3">{t("concentration_trend")}</h4>
          <div className="flex items-end gap-1 h-20">
            {trend.map((w) => {
              const lo = Math.min(...trend.map(x => x.whale_1000));
              const hi = Math.max(...trend.map(x => x.whale_1000));
              const range = hi - lo || 1;
              const h = 20 + ((w.whale_1000 - lo) / range) * 80;
              return (
                <div key={w.date} className="flex-1 flex flex-col items-center justify-end group relative">
                  <div className="w-full bg-signal/50 group-hover:bg-signal rounded-t transition-colors" style={{ height: `${h}%` }} />
                  <div className="absolute -top-5 hidden group-hover:block text-[9px] font-mono whitespace-nowrap bg-surface px-1 rounded">{w.whale_1000.toFixed(1)}%</div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[9px] text-muted mt-1">
            <span>{trend[0].date.slice(5)}</span>
            <span>{trend[trend.length - 1].date.slice(5)}</span>
          </div>
        </div>
      )}

      {/* Per-level breakdown */}
      <div className="card-atmospheric p-4">
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 text-[10px] text-muted mb-2 font-medium">
          <span>{t("holders_level")}</span>
          <span className="text-right">{t("holders_people")}</span>
          <span className="text-right w-16">{t("holders_pct")}</span>
        </div>
        <div className="space-y-1.5">
          {[...data.levels].reverse().map((lv) => (
            <div key={lv.level} className="grid grid-cols-[1fr_auto_auto] gap-x-3 items-center text-[11px]">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 bg-signal/10 rounded" style={{ width: `${(lv.people / maxPeople) * 100}%` }} />
                <span className="relative font-mono">{lv.level}</span>
              </div>
              <span className="text-right font-mono text-muted">{lv.people.toLocaleString()}</span>
              <span className="text-right font-mono font-medium w-16">{lv.percent.toFixed(2)}%</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-muted mt-3">{t("chip_trend_note")}</p>
      </div>
    </div>
  );
}
