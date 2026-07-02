"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface Strategy { id: string; name: string; name_en: string; desc: string; desc_en: string; }
interface BacktestResult { k: string; r5: number; r20: number; r60: number; win: number; triggers: number; }

export function BacktestRanking() {
  const t = useTranslations("data");
  const [activeStrategy, setActiveStrategy] = useState<string>("ma_golden_cross");

  const { data: strategies = [] } = useQuery({
    queryKey: queryKeys.backtest.strategies(),
    queryFn: () => apiFetch<{ data: Strategy[] }>("/screener/backtest/strategies").then(r => r.data || []),
    staleTime: 60 * 60 * 1000,
  });

  const { data: results = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.backtest.byStrategy(activeStrategy),
    queryFn: () => apiFetch<{ data: BacktestResult[] }>(`/screener/backtest?strategy=${activeStrategy}`).then(r => r.data || []),
    staleTime: 10 * 60 * 1000,
  });

  const activeInfo = strategies.find((s) => s.id === activeStrategy);

  return (
    <div className="space-y-6">
      {/* Strategy selector */}
      <div className="card-atmospheric p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-semibold">{t("backtest_title")}</span>
        </div>

        {/* Strategy pills */}
        <div className="flex flex-wrap gap-2 mb-5">
          {strategies.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveStrategy(s.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-colors ${
                activeStrategy === s.id
                  ? "bg-signal/15 text-signal border border-signal/30"
                  : "text-muted hover:text-foreground border border-border/40 hover:border-border"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>

        {/* Strategy description */}
        {activeInfo && (
          <p className="text-xs text-muted mb-4">
            {t("backtest_desc", { name: activeInfo.name })}
          </p>
        )}

        {/* Results table */}
        {loading ? (
          <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 animate-shimmer rounded-xl" />)}</div>
        ) : results.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted">{t("no_data")}</div>
        ) : (
          <div className="border border-border/40 rounded-2xl overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-raised/50">
                  <th className="px-3 py-2.5 text-left text-muted">{t("backtest_rank")}</th>
                  <th className="px-3 py-2.5 text-right text-muted">{t("backtest_5d")}</th>
                  <th className="px-3 py-2.5 text-right text-muted">{t("backtest_20d")}</th>
                  <th className="px-3 py-2.5 text-right text-muted">{t("backtest_60d")}</th>
                  <th className="px-3 py-2.5 text-right text-muted">{t("backtest_winrate")}</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={r.k} className="border-b border-border/30 hover:bg-raised/30">
                    <td className="px-3 py-2.5">
                      <span className="font-mono text-signal mr-2">{i + 1}</span>
                      <span className="font-semibold">{r.k}</span>
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${r.r5 >= 0 ? "text-up" : "text-down"}`}>
                      {r.r5 > 0 ? "+" : ""}{r.r5}%
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${r.r20 >= 0 ? "text-up" : "text-down"}`}>
                      {r.r20 > 0 ? "+" : ""}{r.r20}%
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${r.r60 >= 0 ? "text-up" : "text-down"}`}>
                      {r.r60 > 0 ? "+" : ""}{r.r60}%
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-10 h-1.5 bg-raised rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${r.win >= 65 ? "bg-up" : "bg-signal"}`} style={{ width: `${r.win}%` }} />
                        </div>
                        <span className="font-mono font-bold">{r.win}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Strategy explanation cards */}
      {strategies.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {strategies.map((s) => (
            <div
              key={s.id}
              className={`card-atmospheric p-4 ${activeStrategy === s.id ? "border-signal/30" : ""}`}
            >
              <div className={`text-xs font-bold mb-1.5 ${activeStrategy === s.id ? "text-signal" : "text-foreground"}`}>{s.name}</div>
              <div className="text-[11px] text-muted leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
