"use client";

import { useTranslations } from "next-intl";
import { useStockBars } from "@/hooks/useStockBars";
import { CandlestickCell } from "@/components/market/CandlestickCell";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    close?: number;
    change?: number;
    change_pct?: number;
    prev_close?: number;
    open?: number;
    high?: number;
    low?: number;
    market_cap?: string;
    pe_ratio?: number;
    day_range?: string;
    volume?: number;
    dividend_yield?: number;
    week52_range?: string;
    eps?: number;
  };
}

export function StockCard({ data }: Props) {
  const t = useTranslations("chat");
  const isUp = (data.change_pct || 0) >= 0;

  // Shared, cache-backed bar hook (same one the rankings/watchlist use) instead of
  // a bespoke useEffect+fetch — so the 20-pt sparkline is deduped across the app.
  const bars = useStockBars([data.stock_id]);
  const sparkline = bars[data.stock_id]?.spark ?? [];

  const dayRange = data.day_range || (data.low && data.high ? `${data.low}–${data.high}` : undefined);

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface shadow-sm max-w-lg">
      {/* Header: Name + Price */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-raised flex items-center justify-center text-xs font-bold text-foreground/70 border border-border/30">
              {data.stock_id.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="text-sm font-semibold">{data.stock_name || data.stock_id}</div>
              <div className="text-[10px] text-muted font-mono">{data.stock_id} · TWSE</div>
            </div>
            {/* Today's OHLC candlestick (same component as the market page) */}
            {data.open !== undefined && data.high !== undefined && data.low !== undefined && data.close !== undefined && (
              <CandlestickCell open={data.open} high={data.high} low={data.low} close={data.close} />
            )}
          </div>
          <a
            href={`/dashboard/stocks/${data.stock_id}`}
            className="text-[11px] text-signal hover:underline whitespace-nowrap mt-0.5"
          >
            {t("card_view_detail")} →
          </a>
        </div>

        {/* Price + Change */}
        <div className="mt-3 flex items-baseline gap-3">
          <span className="text-2xl font-bold font-mono">
            {data.close?.toLocaleString() || "—"}
          </span>
          <span className={`text-sm font-mono font-semibold ${isUp ? "text-up" : "text-down"}`}>
            {data.change !== undefined && (isUp ? "+" : "")}{data.change?.toFixed(2) || ""}
          </span>
          <span className={`text-sm font-mono ${isUp ? "text-up" : "text-down"}`}>
            {isUp ? "↗" : "↘"} {Math.abs(data.change_pct || 0).toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Mini Sparkline Chart */}
      {sparkline.length > 5 && (
        <div className="px-4 py-2">
          <MiniChart data={sparkline} isUp={isUp} prevClose={data.prev_close} />
        </div>
      )}

      {/* Key Metrics Grid */}
      <div className="px-4 pb-3 pt-1">
        <div className="grid grid-cols-3 gap-x-4 gap-y-2 text-xs border-t border-border/40 pt-3">
          <Metric label={t("card_prev_close")} value={data.prev_close?.toLocaleString()} />
          <Metric label={t("card_market_cap")} value={data.market_cap} />
          <Metric label={t("card_open")} value={data.open?.toLocaleString()} />
          <Metric label={t("card_pe")} value={data.pe_ratio?.toFixed(2)} />
          <Metric label={t("card_day_range")} value={dayRange} />
          <Metric label={t("card_yield")} value={data.dividend_yield ? `${data.dividend_yield}%` : undefined} />
          <Metric label={t("card_52w")} value={data.week52_range} />
          <Metric label="EPS" value={data.eps ? `$${data.eps.toFixed(2)}` : undefined} />
          <Metric label={t("card_volume")} value={data.volume ? formatVolume(data.volume) : undefined} />
        </div>
      </div>
    </div>
  );
}

function MiniChart({ data, isUp, prevClose }: { data: number[]; isUp: boolean; prevClose?: number }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const h = 60;
  const w = 300;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 8) - 4;
    return `${x},${y}`;
  }).join(" ");

  const fillPoints = `0,${h} ${points} ${w},${h}`;
  const color = isUp ? "var(--up)" : "var(--down)";

  // Prev close reference line
  let prevY: number | undefined;
  if (prevClose && prevClose >= min && prevClose <= max) {
    prevY = h - ((prevClose - min) / range) * (h - 8) - 4;
  }

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[60px]" preserveAspectRatio="none">
      {/* Fill area */}
      <polygon points={fillPoints} fill={color} opacity="0.08" />
      {/* Line */}
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" />
      {/* Prev close dashed line */}
      {prevY !== undefined && (
        <line x1="0" y1={prevY} x2={w} y2={prevY} stroke="var(--muted)" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.5" />
      )}
    </svg>
  );
}

function Metric({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-muted">{label}</span>
      <span className="font-mono font-medium text-foreground">{value || "—"}</span>
    </div>
  );
}

function formatVolume(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(0)}K`;
  return v.toLocaleString();
}
