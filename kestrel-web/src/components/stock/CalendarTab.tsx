"use client";

import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useMarketData } from "@/hooks/useMarketData";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { YfCalendar } from "@/types";

interface DividendRow {
  date: string;
  CashExDividendTradingDate?: string;
  CashDividendPaymentDate?: string;
  StockExDividendTradingDate?: string;
}

interface CalendarEvent {
  date: string;
  label: string;
  type: "earnings" | "dividend" | "ex_dividend" | "other";
}

export function CalendarTab({ stockId }: { stockId: string }) {
  const t = useTranslations("stock");
  const td = useTranslations("data");
  const { data, loading } = useMarketData<DividendRow>(`/fundamentals/${stockId}/dividend`, { start_date: "2024-01-01" });
  const { data: yfCalendar } = useQuery({
    queryKey: queryKeys.yf.calendar(stockId),
    queryFn: () => apiFetch<{ data: YfCalendar }>(`/international/yf/${stockId}/calendar`).then(r => r.data).catch(() => null),
    staleTime: 60 * 60 * 1000,
  });

  // Build events from FinMind dividend data
  const events: CalendarEvent[] = [];
  for (const d of data) {
    if (d.CashExDividendTradingDate) events.push({ date: d.CashExDividendTradingDate, label: t("calendar_ex_dividend"), type: "ex_dividend" });
    if (d.CashDividendPaymentDate) events.push({ date: d.CashDividendPaymentDate, label: t("calendar_dividend_pay"), type: "dividend" });
  }

  // Add yfinance calendar events (earnings date, dividend date)
  if (yfCalendar) {
    if (yfCalendar["Earnings Date"]) {
      const dates = Array.isArray(yfCalendar["Earnings Date"]) ? yfCalendar["Earnings Date"] : [yfCalendar["Earnings Date"]];
      for (const d of dates) {
        if (d) events.push({ date: String(d).split("T")[0], label: t("calendar_earnings"), type: "earnings" });
      }
    }
    if (yfCalendar["Ex-Dividend Date"]) {
      events.push({ date: String(yfCalendar["Ex-Dividend Date"]).split("T")[0], label: t("calendar_ex_dividend"), type: "ex_dividend" });
    }
    if (yfCalendar["Dividend Date"]) {
      events.push({ date: String(yfCalendar["Dividend Date"]).split("T")[0], label: t("calendar_dividend_pay"), type: "dividend" });
    }
  }

  // Deduplicate by date+type and sort
  const seen = new Set<string>();
  const unique = events.filter((e) => {
    const key = `${e.date}-${e.type}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const sorted = unique.sort((a, b) => b.date.localeCompare(a.date));

  if (loading) return <div className="h-40 animate-shimmer rounded-2xl" />;

  if (!sorted.length) return <p className="text-sm text-muted text-center py-10">{td("no_data")}</p>;

  const TYPE_COLORS = {
    earnings: "bg-signal",
    dividend: "bg-up",
    ex_dividend: "bg-legendary",
    other: "bg-muted",
  };

  // Earnings estimates from yfinance. Calendar values arrive as a loose union
  // (string | number | string[]); coerce to a number for the numeric fields.
  const num = (v: string | number | string[] | null | undefined): number | null =>
    typeof v === "number" ? v : typeof v === "string" ? parseFloat(v) || null : null;
  const earningsEstimate = yfCalendar?.["Earnings Average"] || yfCalendar?.["Earnings High"];

  return (
    <div className="space-y-4">
      {/* Upcoming earnings highlight */}
      {yfCalendar?.["Earnings Date"] && (
        <div className="card-atmospheric p-4 border-l-4 border-l-signal">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold">{t("calendar_next_earnings")}</div>
              <div className="text-lg font-bold font-mono mt-1">
                {Array.isArray(yfCalendar["Earnings Date"]) ? yfCalendar["Earnings Date"][0] : yfCalendar["Earnings Date"]}
              </div>
            </div>
            {earningsEstimate && (
              <div className="text-right">
                <div className="text-[10px] text-muted">{t("calendar_eps_estimate")}</div>
                <div className="text-sm font-mono font-bold">
                  {num(yfCalendar["Earnings Low"])?.toFixed(2)} ~ {num(yfCalendar["Earnings High"])?.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Events timeline */}
      <div className="space-y-0.5">
        {sorted.map((e, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-2.5 border-b border-border/20">
            <div className={`w-2.5 h-2.5 rounded-full ${TYPE_COLORS[e.type]}`} />
            <span className="text-xs font-mono text-muted w-24">{e.date}</span>
            <span className="text-xs flex-1">{e.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
