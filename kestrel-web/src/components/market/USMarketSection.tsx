"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useMarketData } from "@/hooks/useMarketData";
import { useUsQuote, quoteChange } from "@/hooks/useUsQuote";
import { daysAgo } from "@/lib/date";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { IndexCard } from "./IndexCard";
import { FearGreedGauge } from "./FearGreedGauge";

interface USPriceRow { date: string; Close: number; High: number; Low: number; Open: number; Volume: number; stock_id: string; }
interface EarningsItem { symbol?: string; company?: string; date?: string; eps_estimate?: number; }

/** One index card: daily `/price` drives the sparkline + close fallback, and the
 *  live fast-info quote (polled 10s while the US market is open) overrides the
 *  value/change so the figure is real-time during trading hours, last close after. */
function UsIndexCard({ symbol, label, code }: { symbol: string; label: string; code: string }) {
  const monthAgo = daysAgo(30);
  // `^` must be percent-encoded in the path segment (^GSPC → %5EGSPC).
  const { data } = useMarketData<USPriceRow>(`/international/us/${encodeURIComponent(symbol)}/price`, { start_date: monthAgo });
  const { quote } = useUsQuote(symbol);

  const latest = data[data.length - 1];
  const prev = data.length > 1 ? data[data.length - 2] : undefined;
  const spark = data.slice(-20).map((r) => r.Close).filter(Boolean);

  // Prefer the live quote; fall back to the latest two daily closes.
  const live = quoteChange(quote);
  const value = quote?.last_price ?? latest?.Close ?? null;
  const change = live.change ?? (latest && prev ? latest.Close - prev.Close : undefined);
  const changePct = live.changePct ?? (latest && prev ? ((latest.Close - prev.Close) / prev.Close) * 100 : undefined);

  return <IndexCard label={label} code={code} value={value} change={change} changePct={changePct} sparkData={spark} />;
}

export function USMarketSection() {
  return (
    <div className="space-y-6">
      {/* US Index cards — live fast-info while the US market is open, last close otherwise */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <UsIndexCard symbol="^GSPC" label="S&P 500" code="SPX" />
        <UsIndexCard symbol="^IXIC" label="Nasdaq" code="QQQ" />
        <UsIndexCard symbol="^DJI" label="Dow Jones" code="DJI" />
        <UsIndexCard symbol="^SOX" label="Philadelphia SOX" code="SOXX" />
      </div>

      {/* 2-column: Yield Curve + Fear/Greed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <YieldCurve />
        </div>
        <FearGreedGauge />
      </div>

      {/* US Hot Stocks — expanded */}
      <USHotStocks />

      {/* Earnings Calendar */}
      <EarningsCalendar />
    </div>
  );
}

function YieldCurve() {
  type CurveData = { current: { label: string; value: number | null }[]; week_ago: { label: string; value: number | null }[]; month_ago: { label: string; value: number | null }[] };
  const { data: curveData, isLoading: loading } = useQuery<CurveData>({
    queryKey: queryKeys.macro.bondsYieldCurve(),
    queryFn: () => apiFetch<{ data: CurveData }>("/macro/bonds/yield-curve").then(res => res.data),
    staleTime: 30 * 60 * 1000,
  });

  if (loading || !curveData) return (
    <div className="card-atmospheric p-5 h-[260px]">
      <span className="text-sm font-semibold">US Treasury Yield Curve</span>
      <div className="h-[200px] animate-shimmer rounded mt-3" />
    </div>
  );

  const { current, week_ago, month_ago } = curveData;
  const allValues = [...current, ...week_ago, ...month_ago].map(p => p.value).filter(Boolean) as number[];
  const minY = Math.min(...allValues) - 0.2;
  const maxY = Math.max(...allValues) + 0.2;
  const rangeY = maxY - minY || 1;

  const w = 400;
  const h = 160;
  const pad = { top: 10, bottom: 25, left: 5, right: 5 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;

  const getX = (i: number) => pad.left + (i / (current.length - 1)) * chartW;
  const getY = (v: number | null) => v != null ? pad.top + chartH - ((v - minY) / rangeY) * chartH : null;

  const buildPath = (points: { label: string; value: number | null }[]) => {
    const coords = points.map((p, i) => ({ x: getX(i), y: getY(p.value) })).filter(c => c.y != null);
    if (coords.length < 2) return "";
    return coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`).join(" ");
  };

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold">US Treasury Yield Curve</span>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-signal rounded" />Current</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-muted/60 rounded" />1W ago</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-muted/30 rounded" />1M ago</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[160px]">
        {[0.25, 0.5, 0.75].map((frac) => (
          <line key={frac} x1={pad.left} y1={pad.top + chartH * frac} x2={w - pad.right} y2={pad.top + chartH * frac} stroke="var(--border)" strokeWidth="0.5" opacity="0.3" />
        ))}
        <path d={buildPath(month_ago)} fill="none" stroke="var(--muted)" strokeWidth="1" opacity="0.3" strokeDasharray="3,3" />
        <path d={buildPath(week_ago)} fill="none" stroke="var(--muted)" strokeWidth="1.2" opacity="0.6" />
        <path d={buildPath(current)} fill="none" stroke="var(--signal)" strokeWidth="2" />
        {current.map((p, i) => {
          const y = getY(p.value);
          if (y == null) return null;
          return <circle key={i} cx={getX(i)} cy={y} r="3" fill="var(--signal)" />;
        })}
        {current.map((p, i) => (
          <text key={i} x={getX(i)} y={h - 4} textAnchor="middle" className="text-[8px] fill-muted/60">{p.label}</text>
        ))}
        {current.map((p, i) => {
          const y = getY(p.value);
          if (y == null || !p.value) return null;
          return <text key={`v${i}`} x={getX(i)} y={y - 8} textAnchor="middle" className="text-[7px] fill-signal font-mono">{p.value.toFixed(2)}</text>;
        })}
      </svg>
    </div>
  );
}

const US_STOCKS = ["NVDA", "AAPL", "TSLA", "MSFT", "META", "GOOGL"];

function USHotStocks() {
  const tm = useTranslations("market");
  const weekAgo = daysAgo(7);

  const queries = US_STOCKS.map((sym) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useMarketData<{ date: string; Close: number }>(`/international/us/${sym}/price`, { start_date: weekAgo })
  );

  const rows = US_STOCKS.map((symbol, i) => {
    const data = queries[i].data;
    const latest = data[data.length - 1];
    const prev = data.length > 1 ? data[data.length - 2] : undefined;
    const pct = latest && prev ? ((latest.Close - prev.Close) / prev.Close) * 100 : 0;
    const spark = data.slice(-5).map((r) => r.Close).filter(Boolean);
    return { symbol, close: latest?.Close || 0, changePct: pct, spark };
  }).filter((r) => r.close > 0);

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-5 py-4 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("us_hot")}</span>
      </div>
      {rows.length === 0 ? (
        <div className="p-8 animate-shimmer h-[100px]" />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-4">
          {rows.map((r) => {
            const isUp = r.changePct >= 0;
            return (
              <div key={r.symbol} className="card-atmospheric p-3 flex flex-col items-center gap-1">
                <span className="text-xs font-mono font-bold text-signal">{r.symbol}</span>
                <span className="text-sm font-mono font-medium">${r.close.toLocaleString()}</span>
                <span className={`text-[10px] font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{r.changePct.toFixed(2)}%
                </span>
                {/* Mini sparkline */}
                {r.spark.length > 1 && (
                  <svg viewBox="0 0 40 16" className="w-10 h-4">
                    <polyline
                      points={r.spark.map((v, i) => {
                        const min = Math.min(...r.spark);
                        const max = Math.max(...r.spark);
                        const range = max - min || 1;
                        return `${(i / (r.spark.length - 1)) * 40},${14 - ((v - min) / range) * 12}`;
                      }).join(" ")}
                      fill="none"
                      stroke={isUp ? "var(--up)" : "var(--down)"}
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EarningsCalendar() {
  const tm = useTranslations("market");

  const { data: earnings = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.intl.earningsCalendar(),
    // Guard: the API may return a non-array `data` (error envelope / unexpected
    // shape) — coerce to [] so the render's .slice never throws.
    queryFn: () => apiFetch<{ data: EarningsItem[] }>("/international/yf/calendar/earnings")
      .then(r => (Array.isArray(r.data) ? r.data : [])),
    staleTime: 60 * 60 * 1000,
  });

  if (loading) return <div className="card-atmospheric p-5 h-[200px] animate-shimmer" />;
  if (earnings.length === 0) return null;

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-5 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("earnings_calendar")}</span>
      </div>
      <div className="divide-y divide-border/10 max-h-[250px] overflow-y-auto">
        {earnings.slice(0, 12).map((e, i) => (
          <div key={i} className="flex items-center gap-3 px-5 py-2.5 hover:bg-raised/30 transition-colors">
            <span className="text-xs font-mono font-bold text-signal w-12">{e.symbol || ""}</span>
            <span className="text-xs text-foreground/80 flex-1 truncate">{e.company || ""}</span>
            <span className="text-[10px] font-mono text-muted">{e.date?.slice(5) || ""}</span>
            {e.eps_estimate !== undefined && (
              <span className="text-[10px] font-mono text-muted/60">est. ${e.eps_estimate}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
