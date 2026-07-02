"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";

interface PerRow {
  date: string;
  PER?: number; per?: number;
  PBR?: number; pbr?: number;
  dividend_yield?: number;
}

interface Series { date: string; value: number }

interface MetricStats {
  key: "per" | "pbr" | "yield";
  label: string;
  riverLabel: string;
  series: Series[];
  current: number;
  min: number;
  max: number;
  avg: number;
  std: number;
  /** 0–100: where `current` sits within [min, max]. */
  percentile: number;
  /** For yield, a high value is CHEAP (inverted), so the verdict flips. */
  inverted: boolean;
  fmt: (v: number) => string;
}

/** 研究圖表 → Valuation analysis. The signature TW-broker research chart: a 2-year
 *  band ("river") of P/E, P/B and dividend yield with the ±1σ range shaded, the
 *  mean line, today's marker, and a percentile gauge telling you whether the stock
 *  is historically cheap or expensive. Built entirely from the /stocks/{id}/per
 *  feed (≈2 years of daily PER/PBR/yield) — no new backend needed. */
export function ValuationTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  const start = daysAgo(730);
  const { data, loading } = useMarketData<PerRow>(`/stocks/${stockId}/per`, { start_date: start });

  const metrics = useMemo<MetricStats[]>(() => {
    const build = (
      key: MetricStats["key"],
      label: string,
      riverLabel: string,
      pick: (r: PerRow) => number | undefined,
      inverted: boolean,
      fmt: (v: number) => string,
    ): MetricStats | null => {
      const series: Series[] = [];
      for (const r of data) {
        const v = pick(r);
        if (typeof v === "number" && Number.isFinite(v) && v > 0) series.push({ date: r.date, value: v });
      }
      if (series.length < 5) return null;
      const values = series.map((s) => s.value);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const std = Math.sqrt(values.reduce((a, b) => a + (b - avg) ** 2, 0) / values.length);
      const current = values[values.length - 1];
      const percentile = max > min ? ((current - min) / (max - min)) * 100 : 50;
      return { key, label, riverLabel, series, current, min, max, avg, std, percentile, inverted, fmt };
    };

    const out: (MetricStats | null)[] = [
      build("per", t("valuation_metric_per"), t("valuation_per_river"), (r) => r.PER ?? r.per, false, (v) => v.toFixed(1)),
      build("pbr", t("valuation_metric_pbr"), t("valuation_pbr_river"), (r) => r.PBR ?? r.pbr, false, (v) => v.toFixed(2)),
      build("yield", t("valuation_metric_yield"), t("valuation_yield_river"), (r) => r.dividend_yield, true, (v) => `${v.toFixed(2)}%`),
    ];
    return out.filter((m): m is MetricStats => m !== null);
  }, [data, t]);

  if (loading) return <div className="h-64 animate-shimmer rounded-2xl" />;
  if (!metrics.length) return <p className="text-sm text-muted text-center py-10">{t("no_data")}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t("valuation_title")}</h3>
      </div>
      {metrics.map((m) => <ValuationCard key={m.key} m={m} t={t} />)}
      <p className="text-[10px] text-muted leading-relaxed">{t("valuation_note")}</p>
    </div>
  );
}

function ValuationCard({ m, t }: { m: MetricStats; t: (k: string) => string }) {
  // Verdict: for P/E & P/B high percentile = expensive; for yield it's inverted.
  const rawPct = m.percentile;
  const expensiveScore = m.inverted ? 100 - rawPct : rawPct;
  const verdict =
    expensiveScore >= 67 ? { label: t("valuation_expensive"), color: "text-down", bg: "bg-down" }
    : expensiveScore <= 33 ? { label: t("valuation_cheap"), color: "text-up", bg: "bg-up" }
    : { label: t("valuation_fair"), color: "text-legendary", bg: "bg-legendary" };

  return (
    <div className="card-atmospheric p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold">{m.riverLabel}</h4>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted">{t("valuation_current")}</span>
          <span className="text-sm font-mono font-bold">{m.fmt(m.current)}</span>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface ${verdict.color}`}>{verdict.label}</span>
        </div>
      </div>

      <BandChart m={m} />

      {/* Stat row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <Stat label={t("valuation_low")} value={m.fmt(m.min)} />
        <Stat label={t("valuation_avg")} value={m.fmt(m.avg)} />
        <Stat label={t("valuation_high")} value={m.fmt(m.max)} />
      </div>

      {/* Percentile gauge */}
      <div>
        <div className="flex items-center justify-between text-[10px] text-muted mb-1">
          <span>{t("valuation_percentile")}</span>
          <span className="font-mono font-medium">{rawPct.toFixed(0)}%</span>
        </div>
        <div className="relative h-2 rounded-full bg-gradient-to-r from-up/40 via-legendary/40 to-down/40">
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full ${verdict.bg} ring-2 ring-surface`}
            style={{ left: `${Math.min(Math.max(rawPct, 2), 98)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-raised/40 py-1.5">
      <div className="text-[9px] text-muted">{label}</div>
      <div className="text-xs font-mono font-medium">{value}</div>
    </div>
  );
}

/** The "river": a filled ±1σ band around the mean, the mean line, and the metric
 *  line over time, with today's point marked. SVG with a 0..100 viewBox so it
 *  scales to any width. */
function BandChart({ m }: { m: MetricStats }) {
  const W = 100, H = 40;
  const lo = m.min, hi = m.max, range = hi - lo || 1;
  const n = m.series.length;
  const x = (i: number) => (i / (n - 1)) * W;
  const y = (v: number) => H - ((v - lo) / range) * H;

  const line = m.series.map((s, i) => `${x(i).toFixed(2)},${y(s.value).toFixed(2)}`).join(" ");
  const bandTop = y(Math.min(m.avg + m.std, hi));
  const bandBot = y(Math.max(m.avg - m.std, lo));
  const meanY = y(m.avg);
  const lastUp = m.series[n - 1].value >= m.series[0].value;
  const stroke = lastUp ? "var(--down)" : "var(--up)"; // rising valuation = redder (more expensive)

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={120} preserveAspectRatio="none" className="overflow-visible">
        {/* ±1σ band */}
        <rect x={0} y={bandTop} width={W} height={Math.max(bandBot - bandTop, 0.5)} fill="var(--signal)" opacity={0.08} />
        {/* mean line (dashed) */}
        <line x1={0} y1={meanY} x2={W} y2={meanY} stroke="var(--muted)" strokeWidth={0.4} strokeDasharray="2 2" opacity={0.5} />
        {/* value line */}
        <polyline points={line} fill="none" stroke={stroke} strokeWidth={0.8} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {/* today marker */}
        <circle cx={x(n - 1)} cy={y(m.current)} r={1.4} fill={stroke} vectorEffect="non-scaling-stroke" />
      </svg>
      {/* date range labels */}
      <div className="flex justify-between text-[9px] text-muted mt-1">
        <span className="font-mono">{m.series[0].date}</span>
        <span className="font-mono">{m.series[n - 1].date}</span>
      </div>
    </div>
  );
}
