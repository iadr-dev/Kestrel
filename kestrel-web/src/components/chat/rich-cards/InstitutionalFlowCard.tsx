"use client";

import { useTranslations } from "next-intl";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    dates: string[];
    foreign_net?: number[];
    trust_net?: number[];
    dealer_net?: number[];
    unit?: string;
  };
}

// Series color + i18n label key (resolved at render via t()).
const SERIES = [
  { key: "foreign_net", i18nKey: "foreign", color: "#4a90d9" },
  { key: "trust_net", i18nKey: "trust", color: "#f5a623" },
  { key: "dealer_net", i18nKey: "dealer", color: "#9b59b6" },
] as const;

export function InstitutionalFlowCard({ data }: Props) {
  const t = useTranslations("data");
  const { stock_id, stock_name, dates } = data;
  const unit = data.unit ?? t("unit_lot_label");
  const series = SERIES.map((s) => ({ ...s, label: t(s.i18nKey), values: (data[s.key] as number[] | undefined) || [] }))
    .filter((s) => s.values.length > 0);
  if (series.length === 0 || !dates?.length) return null;

  const n = dates.length;
  const width = 340;
  const height = 120;
  const pad = { top: 8, right: 8, bottom: 18, left: 8 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const zeroY = pad.top + chartH / 2;

  const allVals = series.flatMap((s) => s.values.map(Math.abs));
  const max = Math.max(...allVals, 1);

  const slot = chartW / n;
  const groupW = slot * 0.7;
  const barW = Math.max(groupW / series.length, 1);

  // Cumulative net per investor for the header summary.
  const totals = series.map((s) => ({ label: s.label, color: s.color, sum: s.values.reduce((a, b) => a + (b || 0), 0) }));

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-3 max-w-md">
      <div className="flex items-baseline justify-between mb-1">
        <div className="text-sm font-semibold">
          {stock_name || stock_id} {t("card_inst_flow")} <span className="text-[10px] text-muted font-mono">{stock_id}</span>
        </div>
        <div className="text-[9px] text-muted">{unit}</div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        <line x1={pad.left} y1={zeroY} x2={width - pad.right} y2={zeroY} stroke="var(--border)" strokeWidth={0.5} />
        {dates.map((_, i) =>
          series.map((s, si) => {
            const v = s.values[i] || 0;
            const h = (Math.abs(v) / max) * (chartH / 2);
            const x = pad.left + i * slot + (slot - groupW) / 2 + si * barW;
            const y = v >= 0 ? zeroY - h : zeroY;
            return <rect key={`${i}-${si}`} x={x} y={y} width={Math.max(barW - 0.5, 0.5)} height={h} fill={s.color} opacity={0.85} />;
          })
        )}
      </svg>

      <div className="flex items-center justify-between mt-1">
        <span className="text-[9px] text-muted">{dates[0]}</span>
        <span className="flex gap-2 text-[9px]">
          {totals.map((t) => (
            <span key={t.label} style={{ color: t.color }}>
              {t.label} {t.sum >= 0 ? "+" : ""}{t.sum.toLocaleString()}
            </span>
          ))}
        </span>
        <span className="text-[9px] text-muted">{dates[dates.length - 1]}</span>
      </div>
    </div>
  );
}
