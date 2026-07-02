"use client";

import { useTranslations } from "next-intl";

interface Topic {
  name: string;
  score?: number;
  unit?: string;
}

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    overall?: number;
    topics: Topic[];
  };
}

function scoreColor(v: number): string {
  return v >= 70 ? "var(--up)" : v >= 40 ? "var(--signal)" : "var(--down)";
}

export function EsgScorecardCard({ data }: Props) {
  const t = useTranslations("data");
  const { stock_id, stock_name, overall, topics } = data;
  if (!topics?.length) return null;

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs text-muted">{t("card_esg_score")}</span>
          <div className="flex items-baseline gap-1">
            <span className="text-sm font-medium">{stock_id}</span>
            {stock_name && <span className="text-xs text-muted">{stock_name}</span>}
          </div>
        </div>
        {overall != null && (
          <div className="text-right">
            <span className="text-2xl font-bold font-mono" style={{ color: scoreColor(overall) }}>{overall.toFixed(0)}</span>
            <span className="text-xs text-muted">/100</span>
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        {topics.map((t, i) => {
          const v = t.score;
          const hasScore = typeof v === "number";
          const pct = hasScore ? Math.min(Math.max(v, 0), 100) : 0;
          return (
            <div key={i} className="flex items-center gap-2">
              <span className="text-[10px] text-muted w-24 shrink-0 truncate" title={t.name}>{t.name}</span>
              <div className="flex-1 h-2 rounded-full bg-border/40 overflow-hidden">
                {hasScore && (
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: scoreColor(v!) }} />
                )}
              </div>
              <span className="text-[11px] font-mono w-12 text-right">
                {hasScore ? v!.toFixed(0) : "—"}{t.unit ? <span className="text-muted text-[9px]"> {t.unit}</span> : null}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
