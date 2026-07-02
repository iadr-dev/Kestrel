"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";
import { ChartFrame } from "./charts/ChartFrame";

interface ADRow {
  date: string;
  up?: number;
  down?: number;
  limit_up?: number;
  limit_down?: number;
  unchanged?: number;
}

export function AdvanceDeclineHistory() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const today = useTradingDate();

  const { data, loading } = useMarketData<ADRow>("/market/advance-decline/history", { trade_date: today, days: "20" });

  const sorted = loading ? [] : [...data]
    .filter((r) => r.date)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-20);

  if (loading || sorted.length === 0) {
    return (
      <div className="card-atmospheric overflow-hidden h-[350px]">
        <div className="px-4 py-3 border-b border-border/30">
          <span className="text-sm font-semibold">{tm("advance_decline_history")}</span>
        </div>
        <div className="flex-1 flex items-center justify-center h-[280px] text-sm text-muted">
          {loading ? <div className="h-[250px] w-full mx-4 animate-shimmer rounded" /> : t("no_data_non_trading")}
        </div>
      </div>
    );
  }

  const maxTotal = Math.max(
    ...sorted.map((r) => Math.max((r.up || 0) + (r.limit_up || 0), (r.down || 0) + (r.limit_down || 0))),
    1
  );

  const tableData = [...sorted].reverse().slice(0, 10);

  return (
    <div className="card-atmospheric overflow-hidden flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("advance_decline_history")}</span>
      </div>

      {/* Stacked up/down family-count bars on the shared chart frame (taller plot,
          zero baseline, gridlines + ±max 家數 axis). Each day: 漲停+上漲 above the
          line, 下跌+跌停 below; limit moves are the darker sub-segment. The chart
          fills the card's stretched height so there's no blank gap above the table. */}
      {sorted.length > 1 && (
        <div className="px-4 pt-4 pb-2 flex flex-col flex-1 min-h-0">
          <ChartFrame fill yMax={maxTotal} unit={tm("family_count")} dates={sorted.map((r) => r.date)} xLabels="endpoints">
            <div className="absolute inset-0 flex items-stretch gap-0.5">
              {sorted.map((row) => {
                const upH = (((row.up || 0) + (row.limit_up || 0)) / maxTotal) * 100;
                const downH = (((row.down || 0) + (row.limit_down || 0)) / maxTotal) * 100;
                const limitUpH = ((row.limit_up || 0) / maxTotal) * 100;
                const limitDownH = ((row.limit_down || 0) / maxTotal) * 100;
                return (
                  <div
                    key={row.date}
                    className="flex-1 flex flex-col items-center min-w-0 h-full"
                    title={`${row.date.slice(5)} · ${tm("advance")} ${(row.up || 0) + (row.limit_up || 0)} / ${tm("decline")} ${(row.down || 0) + (row.limit_down || 0)}`}
                  >
                    {/* Up (above zero) */}
                    <div className="flex flex-col items-center justify-end w-full h-1/2">
                      <div className="w-full max-w-[9px] flex flex-col items-stretch">
                        {limitUpH > 0 && <div className="rounded-t-sm bg-up" style={{ height: `${limitUpH * 2}%` }} />}
                        <div className="bg-up/55" style={{ height: `${(upH - limitUpH) * 2}%` }} />
                      </div>
                    </div>
                    {/* Down (below zero) */}
                    <div className="flex flex-col items-center justify-start w-full h-1/2">
                      <div className="w-full max-w-[9px] flex flex-col items-stretch">
                        <div className="bg-down/55" style={{ height: `${(downH - limitDownH) * 2}%` }} />
                        {limitDownH > 0 && <div className="rounded-b-sm bg-down" style={{ height: `${limitDownH * 2}%` }} />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ChartFrame>
          <div className="flex items-center gap-3 mt-2 justify-center">
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-up" />{tm("limit_up")}</span>
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-up/55" />{tm("advance")}</span>
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-down/55" />{tm("decline")}</span>
            <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-down" />{tm("limit_down")}</span>
          </div>
        </div>
      )}

      {/* Table */}
      <table className="w-full text-xs">
        <thead>
          <tr className="border-y border-border/30 bg-raised/30">
            <th className="px-4 py-2 text-left text-muted font-medium">{t("date")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("limit_up")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("advance")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("limit_down")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("decline")}</th>
          </tr>
        </thead>
        <tbody>
          {tableData.map((row) => (
            <tr key={row.date} className="border-b border-border/20 hover:bg-raised/20">
              <td className="px-4 py-2.5 font-mono text-muted">{row.date.slice(5)}</td>
              <td className="px-4 py-2.5 text-right font-mono text-up font-bold">{row.limit_up || 0}</td>
              <td className="px-4 py-2.5 text-right font-mono text-up">{row.up || 0}</td>
              <td className="px-4 py-2.5 text-right font-mono text-down font-bold">{row.limit_down || 0}</td>
              <td className="px-4 py-2.5 text-right font-mono text-down">{row.down || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
