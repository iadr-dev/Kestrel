"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";

interface BucketItem { b: string; n: number; up?: boolean; flat?: boolean; }

export function AdvanceDecline() {
  const tm = useTranslations("market");
  const today = useTradingDate();

  const { data: rawData, meta, loading } = useMarketData<BucketItem>("/market/advance-decline", { trade_date: today });
  // The endpoint resolves to the last COMPLETE session (today may be partial / a
  // holiday), so label the card with the date the numbers actually describe.
  const sessionDate = (meta?.trade_date as string) || today;

  // The hook expects array, but this endpoint returns { data, summary }
  // We need to use apiFetch directly for this shape
  // For now, use a workaround: fetch via the hook which extracts .data array

  if (loading || !rawData.length) return (
    <div className="card-atmospheric p-5 h-[280px]">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{tm("advance_decline")}</span>
        <span className="text-[10px] text-muted/60">{sessionDate}</span>
      </div>
      <div className="h-[200px] animate-shimmer rounded" />
    </div>
  );

  const buckets = rawData;
  const maxN = Math.max(...buckets.map((b) => b.n || 0), 1);
  const upCount = buckets.filter((b) => b.up).reduce((s, b) => s + (b.n || 0), 0);
  const downCount = buckets.filter((b) => !b.up && !b.flat).reduce((s, b) => s + (b.n || 0), 0);
  const flatCount = buckets.find((b) => b.flat)?.n || 0;

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{tm("advance_decline")}</span>
        <span className="text-[10px] text-muted/60">{sessionDate}</span>
      </div>

      {/* Bar chart */}
      <div className="flex items-end gap-1 h-[160px] mb-3">
        {buckets.map((bucket, i) => {
          const height = Math.max((bucket.n / maxN) * 100, 2);
          const color = bucket.flat ? "bg-signal" : bucket.up ? "bg-up" : "bg-down";
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
              <span className="text-[9px] font-mono font-bold mb-1" style={{ color: bucket.flat ? "var(--signal)" : bucket.up ? "var(--up)" : "var(--down)" }}>
                {bucket.n > 0 ? bucket.n : ""}
              </span>
              <div
                className={`w-full rounded-t-sm ${color}`}
                style={{ height: `${height}%`, opacity: 0.85 }}
              />
              <span className="text-[7px] text-muted/60 mt-1 leading-tight text-center">{bucket.b}</span>
            </div>
          );
        })}
      </div>

      {/* Footer summary */}
      <div className="flex items-center justify-between pt-3 border-t border-border/30">
        <span className="text-sm font-bold text-down">{tm("decline")} {downCount}</span>
        <span className="text-xs text-muted">{tm("flat_label")} {flatCount}</span>
        <span className="text-sm font-bold text-up">{tm("advance")} {upCount}</span>
      </div>
    </div>
  );
}
