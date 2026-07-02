"use client";

import { useTranslations } from "next-intl";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    dates: string[];
    short_balance?: number[];
    lending_balance?: number[];
    unit?: string;
  };
}

// Line color + i18n label key (resolved at render via t()).
const LINES = [
  { key: "short_balance", i18nKey: "card_short_balance", color: "#e74c3c" },
  { key: "lending_balance", i18nKey: "card_lending_balance", color: "#f5a623" },
] as const;

export function ShortPositionCard({ data }: Props) {
  const t = useTranslations("data");
  const { stock_id, stock_name, dates } = data;
  const unit = data.unit ?? t("unit_lot_label");
  const lines = LINES.map((l) => ({ ...l, label: t(l.i18nKey), values: (data[l.key] as number[] | undefined) || [] }))
    .filter((l) => l.values.length > 0);
  if (lines.length === 0 || !dates?.length) return null;

  const n = dates.length;
  const width = 340;
  const height = 110;
  const pad = { top: 8, right: 8, bottom: 16, left: 8 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;

  const allVals = lines.flatMap((l) => l.values);
  const max = Math.max(...allVals, 1);
  const min = Math.min(...allVals, 0);
  const range = max - min || 1;
  const xAt = (i: number) => pad.left + (n === 1 ? chartW / 2 : (i / (n - 1)) * chartW);
  const yAt = (v: number) => pad.top + (1 - (v - min) / range) * chartH;

  // Trend arrow per line (last vs first).
  const trend = (vals: number[]) => {
    if (vals.length < 2) return "";
    const d = vals[vals.length - 1] - vals[0];
    return d > 0 ? "↑" : d < 0 ? "↓" : "→";
  };

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-3 max-w-md">
      <div className="flex items-baseline justify-between mb-1">
        <div className="text-sm font-semibold">
          {stock_name || stock_id} {t("card_short_trend")}
          <span className="ml-1 text-[10px] text-muted font-mono">{stock_id}</span>
        </div>
        <div className="text-[9px] text-muted">{unit}</div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        {lines.map((l, li) => {
          const pts = l.values.map((v, i) => `${xAt(i)},${yAt(v)}`).join(" ");
          return <polyline key={li} points={pts} fill="none" stroke={l.color} strokeWidth={1.4} strokeLinejoin="round" />;
        })}
      </svg>

      <div className="flex items-center justify-between mt-1">
        <span className="text-[9px] text-muted">{dates[0]}</span>
        <span className="flex gap-2 text-[9px]">
          {lines.map((l) => (
            <span key={l.label} style={{ color: l.color }}>
              {l.label} {trend(l.values)}{l.values[l.values.length - 1]?.toLocaleString()}
            </span>
          ))}
        </span>
        <span className="text-[9px] text-muted">{dates[dates.length - 1]}</span>
      </div>
    </div>
  );
}
