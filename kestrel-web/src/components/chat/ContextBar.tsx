"use client";

import { useTranslations } from "next-intl";

interface Props {
  percentage: number;
  isCompacting: boolean;
  sessionCost?: number;
}

export function ContextBar({ percentage, isCompacting, sessionCost = 0 }: Props) {
  const t = useTranslations("chat");

  // Show once context is meaningful, while compacting, or once the session has
  // accrued any cost (so the running spend is visible even at low context).
  if (percentage < 20 && !isCompacting && sessionCost <= 0) return null;

  const getColor = (pct: number) => {
    if (pct >= 80) return "var(--signal-down, #ef4444)";
    if (pct >= 50) return "var(--signal, #ffd83d)";
    return "var(--signal-up, #22c55e)";
  };

  const color = getColor(percentage);

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 text-[10px] text-muted">
      <span className="shrink-0 uppercase tracking-wider">
        {t("context")}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-border/40 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            isCompacting ? "animate-pulse" : ""
          }`}
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span className="shrink-0 font-mono tabular-nums" style={{ color }}>
        {Math.round(percentage)}%
      </span>
      {isCompacting && (
        <span className="shrink-0 text-signal animate-pulse">
          {t("compacting")}
        </span>
      )}
      {sessionCost > 0 && (
        <span className="shrink-0 font-mono tabular-nums text-muted/60" title={t("session_cost")}>
          ${sessionCost.toFixed(4)}
        </span>
      )}
    </div>
  );
}
