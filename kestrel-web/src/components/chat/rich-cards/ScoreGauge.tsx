"use client";

import { useTranslations } from "next-intl";

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    overall: number;
    technical?: number;
    chip?: number;
    fundamental?: number;
    theme?: number;
  };
}

function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  const color = value >= 80 ? "var(--signal-up)" : value >= 50 ? "var(--signal)" : "var(--signal-down)";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-muted w-8 shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-border/40 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-mono w-6 text-right" style={{ color }}>{value}</span>
    </div>
  );
}

export function ScoreGauge({ data }: Props) {
  const t = useTranslations("chat");
  const overall = data.overall || 0;
  const color = overall >= 75 ? "var(--signal-up)" : overall >= 45 ? "var(--signal)" : "var(--signal-down)";

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs text-muted">{t("ai_score")}</span>
          <div className="flex items-baseline gap-1">
            <span className="text-sm font-medium">{data.stock_id}</span>
            {data.stock_name && <span className="text-xs text-muted">{data.stock_name}</span>}
          </div>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold font-mono" style={{ color }}>{overall}</span>
          <span className="text-xs text-muted">/100</span>
        </div>
      </div>
      <div className="space-y-1.5">
        {data.technical != null && <ScoreBar label={t("score_tech")} value={data.technical} />}
        {data.chip != null && <ScoreBar label={t("score_chip")} value={data.chip} />}
        {data.fundamental != null && <ScoreBar label={t("score_fund")} value={data.fundamental} />}
        {data.theme != null && <ScoreBar label={t("score_theme")} value={data.theme} />}
      </div>
    </div>
  );
}
