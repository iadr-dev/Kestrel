"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";

interface IndexTick {
  stock_id?: string;
  date?: string;
  time?: string;
  price?: number;
  TAIEX?: number;
}

export function MarketTrend() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const today = useTradingDate();

  const { data, loading } = useMarketData<IndexTick>("/market/indices/5sec", {
    trade_date: today,
  });

  // The 5-sec feed is per-sector (stock_id = "Automobile", "Electronic", …) plus an
  // overall "TAIEX" series. Keep only the TAIEX line; rows use lowercase `time`/`price`.
  const ticks = loading ? [] : data
    .filter((d) => d.stock_id === "TAIEX" && d.time && (d.price ?? d.TAIEX))
    .map((d) => ({ time: d.time!, value: d.price ?? d.TAIEX ?? 0 }))
    .sort((a, b) => a.time.localeCompare(b.time));

  if (loading || ticks.length < 2) {
    return (
      <div className="card-atmospheric p-5 h-[220px]">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold">{tm("market_trend_title")}</span>
        </div>
        <div className="flex-1 flex items-center justify-center h-[160px] text-sm text-muted">
          {loading ? <div className="h-full w-full animate-shimmer rounded" /> : t("no_data_non_trading")}
        </div>
      </div>
    );
  }

  const values = ticks.map((t) => t.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const open = values[0];
  const close = values[values.length - 1];
  const change = close - open;
  const changePct = ((change / open) * 100).toFixed(2);
  const isUp = change >= 0;

  const W = 400;
  const H = 140;
  const PX = 8;
  const PY = 12;

  const points = ticks.map((tick, i) => {
    const x = PX + (i / (ticks.length - 1)) * (W - PX * 2);
    const y = PY + (1 - (tick.value - min) / range) * (H - PY * 2);
    return { x, y };
  });

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${H} L ${points[0].x.toFixed(1)} ${H} Z`;

  const timeLabels = [
    { label: "9:00", pct: 0 },
    { label: "10:00", pct: 0.222 },
    { label: "11:00", pct: 0.444 },
    { label: "12:00", pct: 0.667 },
    { label: "13:00", pct: 0.889 },
    { label: "13:30", pct: 1 },
  ];

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{tm("market_trend_title")}</span>
          <span className="text-[10px] text-muted/60">TAIEX 5s</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono font-bold">{close.toLocaleString()}</span>
          <span className={`text-xs font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
            {isUp ? "+" : ""}{change.toFixed(2)} ({isUp ? "+" : ""}{changePct}%)
          </span>
        </div>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[180px]" preserveAspectRatio="none">
          <defs>
            <linearGradient id="taiex-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isUp ? "var(--up)" : "var(--down)"} stopOpacity="0.15" />
              <stop offset="100%" stopColor={isUp ? "var(--up)" : "var(--down)"} stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Open reference line */}
          <line
            x1={PX}
            y1={PY + (1 - (open - min) / range) * (H - PY * 2)}
            x2={W - PX}
            y2={PY + (1 - (open - min) / range) * (H - PY * 2)}
            stroke="var(--border)"
            strokeWidth="0.5"
            strokeDasharray="3 3"
          />

          <path d={areaD} fill="url(#taiex-fill)" />
          <path
            d={pathD}
            fill="none"
            stroke={isUp ? "var(--up)" : "var(--down)"}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* Time axis */}
        <div className="flex justify-between mt-1 px-1">
          {timeLabels.map((tl) => (
            <span key={tl.label} className="text-[9px] font-mono text-muted/50">
              {tl.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
