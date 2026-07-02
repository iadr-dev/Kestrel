"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

interface TierStock {
  stock_id: string;
  stock_name?: string;
  change_pct?: number;
}

interface Props {
  data: {
    theme_id: string;
    theme_name: string;
    stock_count: number;
    today_change_pct?: number;
    tiers?: {
      upstream?: TierStock[];
      midstream?: TierStock[];
      downstream?: TierStock[];
    };
  };
}

function TierColumn({ label, stocks }: { label: string; stocks?: TierStock[] }) {
  if (!stocks || stocks.length === 0) return null;
  return (
    <div className="flex-1 min-w-0">
      <div className="text-[10px] text-muted mb-1">{label} ({stocks.length})</div>
      <div className="space-y-0.5">
        {stocks.slice(0, 4).map((s) => (
          <Link key={s.stock_id} href={`/dashboard/stocks/${s.stock_id}`} className="flex items-center justify-between text-[11px] hover:bg-raised rounded px-1 py-0.5 transition-colors">
            <span className="font-mono">{s.stock_id}</span>
            {s.change_pct != null && (
              <span className={s.change_pct >= 0 ? "text-[var(--signal-up)]" : "text-[var(--signal-down)]"}>
                {s.change_pct >= 0 ? "▲" : "▼"}{Math.abs(s.change_pct).toFixed(1)}%
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

export function ThemeOverviewCard({ data }: Props) {
  const t = useTranslations("chat");
  const changePct = data.today_change_pct;

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-4 max-w-md">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm">📊</span>
          <span className="text-sm font-medium">{data.theme_name}</span>
          <span className="text-[10px] text-muted">({data.stock_count} {t("theme_stocks")})</span>
        </div>
        {changePct != null && (
          <span className={`text-sm font-mono ${changePct >= 0 ? "text-[var(--signal-up)]" : "text-[var(--signal-down)]"}`}>
            {changePct >= 0 ? "▲" : "▼"}{Math.abs(changePct).toFixed(2)}%
          </span>
        )}
      </div>

      {data.tiers && (
        <div className="flex gap-3">
          <TierColumn label={t("tier_upstream")} stocks={data.tiers.upstream} />
          <TierColumn label={t("tier_midstream")} stocks={data.tiers.midstream} />
          <TierColumn label={t("tier_downstream")} stocks={data.tiers.downstream} />
        </div>
      )}
    </div>
  );
}
