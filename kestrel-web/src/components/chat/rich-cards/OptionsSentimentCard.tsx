"use client";

import { useTranslations } from "next-intl";

interface Props {
  data: {
    put_call_ratio: number;
    iv_rank?: number;
    current_iv?: number;
    sentiment?: "extreme_fear" | "fear" | "neutral" | "greed" | "extreme_greed";
    note?: string;
  };
}

// Color per sentiment + the i18n key for its label (resolved at render via t()).
const SENTIMENT_META: Record<string, { i18nKey: string; color: string }> = {
  extreme_fear: { i18nKey: "fear_extreme_fear", color: "#16a085" },
  fear: { i18nKey: "fear_fear", color: "#27ae60" },
  neutral: { i18nKey: "fear_neutral", color: "#95a5a6" },
  greed: { i18nKey: "fear_greed_label", color: "#e67e22" },
  extreme_greed: { i18nKey: "fear_extreme_greed", color: "#e74c3c" },
};

// High P/C ratio = fear (more puts); low = greed. Derive sentiment if absent.
function deriveSentiment(pc: number): keyof typeof SENTIMENT_META {
  if (pc >= 1.3) return "extreme_fear";
  if (pc >= 1.1) return "fear";
  if (pc >= 0.9) return "neutral";
  if (pc >= 0.7) return "greed";
  return "extreme_greed";
}

export function OptionsSentimentCard({ data }: Props) {
  const t = useTranslations("data");
  const { put_call_ratio, iv_rank, current_iv, note } = data;
  if (put_call_ratio == null) return null;

  const sentiment = data.sentiment || deriveSentiment(put_call_ratio);
  const meta = SENTIMENT_META[sentiment] || SENTIMENT_META.neutral;

  // Position on a 0.4–1.6 P/C scale (clamped).
  const lo = 0.4;
  const hi = 1.6;
  const pos = Math.min(Math.max((put_call_ratio - lo) / (hi - lo), 0), 1) * 100;

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-sm">
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-sm font-semibold">{t("card_options_sentiment")}</span>
        <span className="text-sm font-semibold" style={{ color: meta.color }}>{t(meta.i18nKey)}</span>
      </div>

      <div className="flex items-baseline gap-1 mb-1">
        <span className="text-xs text-muted">Put/Call</span>
        <span className="text-2xl font-bold font-mono" style={{ color: meta.color }}>{put_call_ratio.toFixed(2)}</span>
      </div>

      {/* P/C gauge: greed (left) → fear (right) */}
      <div className="relative h-2 rounded-full overflow-hidden mb-1"
        style={{ background: "linear-gradient(90deg, #e74c3c 0%, #e67e22 25%, #95a5a6 50%, #27ae60 75%, #16a085 100%)" }}>
        <div className="absolute top-1/2 -translate-y-1/2 w-1 h-4 bg-foreground rounded" style={{ left: `${pos}%` }} />
      </div>
      <div className="flex justify-between text-[9px] text-muted mb-2">
        <span>{t("card_greed_low_pc")}</span>
        <span>{t("card_fear_high_pc")}</span>
      </div>

      {(iv_rank != null || current_iv != null) && (
        <div className="flex gap-4 text-[11px] border-t border-border/30 pt-2">
          {current_iv != null && (
            <div><span className="text-muted">IV: </span><span className="font-mono">{current_iv.toFixed(1)}%</span></div>
          )}
          {iv_rank != null && (
            <div><span className="text-muted">IV Rank: </span><span className="font-mono">{iv_rank.toFixed(0)}</span></div>
          )}
        </div>
      )}

      {note && <div className="text-[10px] text-muted mt-2">{note}</div>}
    </div>
  );
}
