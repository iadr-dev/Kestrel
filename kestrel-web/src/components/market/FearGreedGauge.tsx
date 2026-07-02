"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";

interface FearGreedRow {
  date: string;
  fear_greed: number;
  fear_greed_emotion: string;
}

const EMOTION_KEYS: Record<string, string> = {
  "Extreme Fear": "fear_extreme_fear",
  "Fear": "fear_fear",
  "Neutral": "fear_neutral",
  "Greed": "fear_greed_label",
  "Extreme Greed": "fear_extreme_greed",
};

const getColor = (v: number) => {
  if (v <= 25) return "#ff5f4a";
  if (v <= 45) return "#ff8c42";
  if (v <= 55) return "#c9a200";
  if (v <= 75) return "#7dd87d";
  return "#5ee885";
};

/** Compact, strip-aligned gauge — sized to match the macro StripCards (same
 *  height/padding) so it sits flush in the macro strip without being clipped. */
export function FearGreedGaugeCompact() {
  const t = useTranslations("data");
  const monthAgo = daysAgo(30);
  const { data, loading } = useMarketData<FearGreedRow>("/macro/fear-greed", { start_date: monthAgo });

  if (loading)
    return <div className="shrink-0 w-[130px] h-full animate-shimmer rounded-xl" />;

  const latest = data[data.length - 1];
  const value = latest?.fear_greed ?? 50;
  const emotion = latest?.fear_greed_emotion ?? "Neutral";
  const angle = -90 + (value / 100) * 180;
  const color = getColor(value);

  return (
    <div className="shrink-0 w-[130px] h-full px-3 py-2 rounded-xl bg-surface/60 border border-border/30 flex flex-col items-center justify-between overflow-hidden">
      <span className="text-[9px] text-muted uppercase tracking-wider truncate w-full text-center">{t("fear_greed")}</span>
      <div className="relative w-[72px] h-[38px] overflow-hidden">
        <svg viewBox="0 0 120 62" className="w-full h-full">
          <path d="M 10 55 A 50 50 0 0 1 110 55" fill="none" stroke="var(--border)" strokeWidth="9" strokeLinecap="round" opacity="0.4" />
          <path d="M 10 55 A 50 50 0 0 1 110 55" fill="none" stroke="url(#gauge-grad)" strokeWidth="9" strokeLinecap="round" />
          <defs>
            <linearGradient id="gauge-grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#ff5f4a" />
              <stop offset="25%" stopColor="#ff8c42" />
              <stop offset="50%" stopColor="#c9a200" />
              <stop offset="75%" stopColor="#7dd87d" />
              <stop offset="100%" stopColor="#5ee885" />
            </linearGradient>
          </defs>
          <line x1="60" y1="55" x2="60" y2="14" stroke={color} strokeWidth="3" strokeLinecap="round"
            transform={`rotate(${angle}, 60, 55)`} className="transition-all duration-1000" />
          <circle cx="60" cy="55" r="4.5" fill={color} />
          <circle cx="60" cy="55" r="2" fill="var(--background)" />
        </svg>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-sm font-mono font-bold" style={{ color }}>{value.toFixed(0)}</span>
        <span className="text-[9px] text-muted truncate">{EMOTION_KEYS[emotion] ? t(EMOTION_KEYS[emotion]) : emotion}</span>
      </div>
    </div>
  );
}

export function FearGreedGauge() {
  const t = useTranslations("data");
  const monthAgo = daysAgo(30);
  const { data, loading } = useMarketData<FearGreedRow>("/macro/fear-greed", {
    start_date: monthAgo,
  });

  if (loading)
    return <div className="card-atmospheric p-5 h-[200px] animate-shimmer" />;

  const latest = data[data.length - 1];
  const value = latest?.fear_greed ?? 50;
  const emotion = latest?.fear_greed_emotion ?? "Neutral";

  const angle = -90 + (value / 100) * 180;
  const color = getColor(value);

  return (
    <div className="card-atmospheric p-5 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background glow based on emotion */}
      <div
        className="absolute inset-0 opacity-20 animate-pulse-slow"
        style={{
          background: `radial-gradient(ellipse at 50% 80%, ${color}40, transparent 70%)`,
        }}
      />

      <span className="text-[10px] uppercase tracking-wider text-muted/60 mb-3 relative z-10">
        {t("fear_greed")}
      </span>

      <div className="relative w-36 h-[72px] overflow-hidden z-10">
        <svg viewBox="0 0 120 62" className="w-full h-full">
          <defs>
            <linearGradient id="gauge-grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#ff5f4a" />
              <stop offset="25%" stopColor="#ff8c42" />
              <stop offset="50%" stopColor="#c9a200" />
              <stop offset="75%" stopColor="#7dd87d" />
              <stop offset="100%" stopColor="#5ee885" />
            </linearGradient>
            <filter id="needle-glow">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Track background */}
          <path
            d="M 10 55 A 50 50 0 0 1 110 55"
            fill="none"
            stroke="var(--border)"
            strokeWidth="9"
            strokeLinecap="round"
            opacity="0.4"
          />

          {/* Colored arc */}
          <path
            d="M 10 55 A 50 50 0 0 1 110 55"
            fill="none"
            stroke="url(#gauge-grad)"
            strokeWidth="9"
            strokeLinecap="round"
          />

          {/* Tick marks */}
          {[0, 25, 50, 75, 100].map((tick) => {
            const a = (-90 + (tick / 100) * 180) * (Math.PI / 180);
            const x1 = 60 + 42 * Math.cos(a);
            const y1 = 55 + 42 * Math.sin(a);
            const x2 = 60 + 47 * Math.cos(a);
            const y2 = 55 + 47 * Math.sin(a);
            return (
              <line
                key={tick}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="var(--foreground)"
                strokeWidth="1"
                opacity="0.3"
              />
            );
          })}

          {/* Needle with glow */}
          <g filter="url(#needle-glow)">
            <line
              x1="60"
              y1="55"
              x2="60"
              y2="14"
              stroke={color}
              strokeWidth="2.5"
              strokeLinecap="round"
              transform={`rotate(${angle}, 60, 55)`}
              className="transition-all duration-1000"
            />
          </g>

          {/* Center dot */}
          <circle cx="60" cy="55" r="4.5" fill={color} />
          <circle cx="60" cy="55" r="2" fill="var(--background)" />
        </svg>
      </div>

      {/* Value with glow effect */}
      <div
        className="text-3xl font-bold font-mono mt-2 relative z-10"
        style={{
          color,
          textShadow: `0 0 12px ${color}60`,
        }}
      >
        {value.toFixed(0)}
      </div>
      <div className="text-xs text-muted mt-1 relative z-10">
        {EMOTION_KEYS[emotion] ? t(EMOTION_KEYS[emotion]) : emotion}
      </div>
    </div>
  );
}
