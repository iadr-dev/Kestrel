"use client";

import { useTranslations, useLocale } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface NavPoint {
  date?: string;
  market_price?: number | null;
  nav?: number | null;
  premium_discount_pct?: number | null;
}

const num = (v: unknown): number | null => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/** Daily 折溢價 (premium/discount) history for a TW ETF.
 *
 * Series is persisted nightly by the backend (etf_nav_daily); the live NAV feed is
 * point-in-time only, so this fills in over time as the ingest runs. Drawn as a
 * hand-rolled SVG (the codebase has no generic charting lib) with a zero baseline —
 * premium (>0) shades up, discount (<0) shades down. `compact` renders an inline
 * card for the overview tab; otherwise a full-height standalone view. */
export function ETFPremiumHistory({
  stockId,
  days = 90,
  compact = false,
}: {
  stockId: string;
  days?: number;
  compact?: boolean;
}) {
  const t = useTranslations("stock");
  const locale = useLocale();

  const { data: points = [], isLoading } = useQuery({
    queryKey: queryKeys.etf.premiumHistory(stockId, days),
    queryFn: () =>
      apiFetch<{ data: NavPoint[] }>(`/etf/${encodeURIComponent(stockId)}/premium-history?days=${days}`)
        .then((r) => r.data || [])
        .catch(() => []),
    staleTime: 30 * 60 * 1000,
  });

  if (isLoading) return <div className={`${compact ? "h-32" : "h-56"} animate-shimmer rounded-2xl`} />;

  const series = points
    .map((p) => ({ date: p.date ?? "", pd: num(p.premium_discount_pct) }))
    .filter((p): p is { date: string; pd: number } => p.pd != null);

  if (series.length === 0) {
    return (
      <div className="card-atmospheric p-4">
        <h4 className="text-xs font-semibold mb-2">{t("etf_premium_history")}</h4>
        <p className="text-xs text-muted text-center py-4">{t("etf_premium_history_empty")}</p>
      </div>
    );
  }

  const values = series.map((p) => p.pd);
  const avg = values.reduce((s, v) => s + v, 0) / values.length;
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const latest = series[series.length - 1];

  return (
    <div className="card-atmospheric p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold">{t("etf_premium_history")}</h4>
        <div className="flex gap-4 text-[10px] text-muted">
          <span>
            {t("etf_avg_premium")}:{" "}
            <span className={`font-mono ${avg >= 0 ? "text-up" : "text-down"}`}>
              {avg >= 0 ? "+" : ""}
              {avg.toFixed(2)}%
            </span>
          </span>
          <span>
            {t("etf_premium_range")}:{" "}
            <span className="font-mono text-foreground/70">
              {min.toFixed(2)}% ~ {max >= 0 ? "+" : ""}
              {max.toFixed(2)}%
            </span>
          </span>
        </div>
      </div>

      <PremiumChart series={series} height={compact ? 96 : 200} locale={locale} />

      {/* Latest reading */}
      <div className="mt-2 flex items-center justify-between text-[10px] text-muted">
        <span>{latest.date}</span>
        <span className={`font-mono ${latest.pd >= 0 ? "text-up" : "text-down"}`}>
          {latest.pd >= 0 ? "+" : ""}
          {latest.pd.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

function PremiumChart({
  series,
  height,
  locale,
}: {
  series: { date: string; pd: number }[];
  height: number;
  locale: string;
}) {
  const w = 320;
  const h = height;
  const values = series.map((p) => p.pd);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const range = max - min || 1;
  const x = (i: number) => (series.length === 1 ? w / 2 : (i / (series.length - 1)) * w);
  const y = (v: number) => h - ((v - min) / range) * h;
  const zeroY = y(0);

  const points = series.map((p, i) => `${x(i)},${y(p.pd)}`).join(" ");
  const isUp = values[values.length - 1] >= 0;

  // Date axis labels (first / mid / last) — localized short date.
  const fmtDate = (s: string) => {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return s;
    return d.toLocaleDateString(locale, { month: "numeric", day: "numeric" });
  };
  const axisIdx = series.length > 2 ? [0, Math.floor(series.length / 2), series.length - 1] : [0, series.length - 1];

  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height }} preserveAspectRatio="none">
        <defs>
          <linearGradient id="pd-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--up)" stopOpacity="0.18" />
            <stop offset={`${(zeroY / h) * 100}%`} stopColor="var(--up)" stopOpacity="0.02" />
            <stop offset={`${(zeroY / h) * 100}%`} stopColor="var(--down)" stopOpacity="0.02" />
            <stop offset="100%" stopColor="var(--down)" stopOpacity="0.18" />
          </linearGradient>
        </defs>
        {/* fill to zero baseline */}
        <polygon points={`${x(0)},${zeroY} ${points} ${x(series.length - 1)},${zeroY}`} fill="url(#pd-grad)" />
        {/* zero baseline */}
        <line x1="0" y1={zeroY} x2={w} y2={zeroY} stroke="var(--border)" strokeWidth="1" strokeDasharray="3 3" />
        <polyline
          points={points}
          fill="none"
          stroke={isUp ? "var(--up)" : "var(--down)"}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="flex justify-between mt-1 text-[9px] text-muted font-mono">
        {axisIdx.map((i) => (
          <span key={i}>{fmtDate(series[i].date)}</span>
        ))}
      </div>
    </div>
  );
}
