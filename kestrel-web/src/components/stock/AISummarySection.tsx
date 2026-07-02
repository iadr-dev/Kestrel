"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { AssetKind } from "@/lib/asset";
import { TierGate } from "@/components/gating/TierGate";
import type { Tier } from "@/lib/entitlements";

interface AISummary {
  stock_id: string;
  position_label: string;
  summary: string;
  factors: { polarity: string; category: string; text: string; importance?: string }[];
  swot: { strengths?: string[]; weaknesses?: string[]; opportunities?: string[]; threats?: string[] };
  generated_at: string | null;
}
interface AIScore {
  stock_id: string;
  kind?: string;
  overall_score: number;
  technical_score?: number | null;
  chip_score?: number | null;
  fundamental_score?: number | null;
  theme_score?: number | null;
  sub_scores?: Record<string, number>;
  caveats?: string[];
}

/** AI Insight — works for ANY asset (TW/US · stock/ETF). Fetches the market-aware
 *  score (resolve-or-compute) + summary from the same /ai endpoints. Shows a score
 *  gauge with the sub-scores that apply to the kind, the position summary, key factors,
 *  SWOT, and any caveats (S/R false-break, news-vs-chip divergence). `kind` is passed as
 *  the `at` hint so US-ETF vs US-stock resolves correctly. */
export function AISummarySection({ stockId, kind }: { stockId: string; kind?: AssetKind }) {
  const t = useTranslations("stock");
  const at = kind ? `?at=${kind}` : "";

  const { data: scoreRes } = useQuery({
    queryKey: queryKeys.ai.score(stockId),
    queryFn: () => apiFetch<{ data: AIScore | null; locked?: boolean; required_tier?: string }>(`/ai/score/${encodeURIComponent(stockId)}${at}`),
    staleTime: 30 * 60 * 1000,
  });
  const { data: summaryRes, isLoading: loading } = useQuery({
    queryKey: queryKeys.ai.summary(stockId),
    queryFn: () => apiFetch<{ data: AISummary | null; locked?: boolean; required_tier?: string }>(`/ai/summary/${encodeURIComponent(stockId)}${at}`),
    staleTime: 30 * 60 * 1000,
  });

  const score = scoreRes?.data ?? null;
  const data = summaryRes?.data ?? null;
  // Server-side gating: either endpoint reporting `locked` means this tier can't see
  // the full AI insight → render the whole section as a frosted teaser.
  const locked = Boolean(scoreRes?.locked || summaryRes?.locked);
  const requiredTier = (scoreRes?.required_tier || summaryRes?.required_tier || "premium") as Tier;

  if (loading && !score) return <div className="card-atmospheric p-4 animate-pulse h-32" />;
  if (!score && !data) {
    return (
      <div className="card-atmospheric p-4 text-center">
        <p className="text-xs text-muted">{t("ai_no_summary")}</p>
      </div>
    );
  }

  const posLabel = data?.position_label ?? "";
  const positionColor = posLabel.includes("多") ? "text-up" : posLabel.includes("空") ? "text-down" : "text-muted";
  const caveats = score?.caveats ?? [];

  // Sub-score bars — market-aware: use whatever sub_scores the resolver returned,
  // falling back to the flat score columns for TW.
  const sub = score?.sub_scores && Object.keys(score.sub_scores).length > 0
    ? score.sub_scores
    : {
        ...(score?.technical_score != null ? { technical: score.technical_score } : {}),
        ...(score?.chip_score != null ? { chip: score.chip_score } : {}),
        ...(score?.fundamental_score != null ? { fundamental: score.fundamental_score } : {}),
        ...(score?.theme_score != null ? { theme: score.theme_score } : {}),
      };

  return (
    <TierGate locked={locked} mode="teaser" requiredTier={requiredTier}>
    <div className="space-y-4">
      {/* Score gauge */}
      {score && (
        <div className="card-atmospheric p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">📊 {t("ai_score_title")}</h3>
            <div className="text-right">
              <span
                className="text-2xl font-bold font-mono"
                style={{ color: score.overall_score >= 75 ? "var(--signal-up)" : score.overall_score >= 45 ? "var(--signal)" : "var(--signal-down)" }}
              >
                {score.overall_score}
              </span>
              <span className="text-xs text-muted">/100</span>
            </div>
          </div>
          <div className="space-y-1.5">
            {Object.entries(sub).map(([k, v]) => <ScoreBar key={k} label={t(`ai_factor_${k}`)} value={v} />)}
          </div>
        </div>
      )}

      {/* Caveats (S/R false-break, news divergence) */}
      {caveats.length > 0 && (
        <div className="card-atmospheric p-4 border-l-2 border-signal/40">
          <h4 className="text-xs font-semibold mb-1.5">⚠️ {t("ai_caveats")}</h4>
          <ul className="space-y-1">
            {caveats.map((c, i) => <li key={i} className="text-[11px] text-muted">• {c}</li>)}
          </ul>
        </div>
      )}

      {/* Summary + position */}
      {data && (
        <div className="card-atmospheric p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">✨ {t("ai_summary_title")}</h3>
            {posLabel && (
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-surface ${positionColor}`}>{posLabel}</span>
            )}
          </div>
          <p className="text-sm leading-relaxed">{data.summary}</p>
          {data.generated_at && (
            <p className="text-[10px] text-muted mt-2">{t("ai_generated_at")}: {data.generated_at}</p>
          )}
        </div>
      )}

      {/* Factors */}
      {data && data.factors.length > 0 && (
        <div className="card-atmospheric p-4">
          <h4 className="text-xs font-semibold mb-2">{t("ai_factors")}</h4>
          <div className="space-y-1.5">
            {data.factors.map((f, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={f.polarity === "positive" ? "text-up" : f.polarity === "negative" ? "text-down" : "text-muted"}>
                  {f.polarity === "positive" ? "▲" : f.polarity === "negative" ? "▼" : "•"}
                </span>
                <span className={f.importance === "key" ? "font-medium" : "text-muted"}>{f.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SWOT */}
      {data?.swot && (data.swot.strengths?.length || data.swot.weaknesses?.length) ? (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: "strengths", label: t("ai_strengths"), items: data.swot.strengths, color: "border-up/30" },
            { key: "weaknesses", label: t("ai_weaknesses"), items: data.swot.weaknesses, color: "border-down/30" },
            { key: "opportunities", label: t("ai_opportunities"), items: data.swot.opportunities, color: "border-signal/30" },
            { key: "threats", label: t("ai_threats"), items: data.swot.threats, color: "border-muted/30" },
          ].map(({ key, label, items, color }) =>
            items && items.length > 0 ? (
              <div key={key} className={`card-atmospheric p-3 border-l-2 ${color}`}>
                <h5 className="text-[10px] font-bold uppercase mb-1">{label}</h5>
                <ul className="space-y-0.5">
                  {items.map((item, i) => <li key={i} className="text-[11px] text-muted">• {item}</li>)}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      ) : null}
    </div>
    </TierGate>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(Math.max(value, 0), 100);
  const color = value >= 80 ? "var(--signal-up)" : value >= 50 ? "var(--signal)" : "var(--signal-down)";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-muted w-16 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-border/40 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-mono w-6 text-right" style={{ color }}>{value}</span>
    </div>
  );
}
