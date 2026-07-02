"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { isTwMarketOpen } from "@/hooks/useTradingDate";
import { daysAgo } from "@/lib/date";
import { normalizeBar } from "@/lib/price";
import type { SnapshotRow, DailyPriceRow } from "@/types";

export function RealtimeTab({ stockId }: { stockId: string }) {
  const t = useTranslations("data");
  // Live snapshot — poll every 10s while the market is open, otherwise fetch once.
  const marketOpen = isTwMarketOpen();
  const { data, loading } = useMarketData<SnapshotRow>(
    `/stocks/${stockId}/snapshot`,
    undefined,
    marketOpen ? { staleTime: 5000, refetchInterval: 10000 } : undefined,
  );
  // Fallback: the snapshot feed is EMPTY when the market is closed (verified), so
  // fall back to the latest daily bar — the UI then shows the last close instead
  // of "no data" on weekends/holidays/after-hours.
  const { data: daily } = useMarketData<DailyPriceRow>(`/stocks/${stockId}/price`, { start_date: daysAgo(7) });

  if (loading) return <p className="text-sm text-muted p-4">{t("loading")}</p>;

  let snap = data[0] || null;
  if (!snap && daily.length > 0) {
    const bar = normalizeBar(daily[daily.length - 1]);
    snap = {
      close: bar.close, open: bar.open, high: bar.high, low: bar.low,
      change_price: bar.spread,
      change_rate: bar.close && bar.spread != null && bar.close - bar.spread !== 0
        ? Number(((bar.spread / (bar.close - bar.spread)) * 100).toFixed(2)) : undefined,
    } as SnapshotRow;
  }
  if (!snap) return <p className="text-sm text-muted p-4">{t("realtime_no_data")}</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {[[t("close"),snap.close],[t("open"),snap.open],[t("high"),snap.high],[t("low"),snap.low],[t("change"),snap.change_price],[t("change")+"%",snap.change_rate?`${snap.change_rate}%`:undefined],[t("volume"),snap.total_volume?.toLocaleString()],["Tick",snap.volume?.toLocaleString()]].map(([l,v])=>(
          <div key={l as string} className="px-3 py-2 border border-border/50 rounded-lg"><div className="text-[10px] text-muted">{l}</div><div className="text-sm font-mono font-medium mt-0.5">{v ?? "—"}</div></div>
        ))}
      </div>
      <div className="border border-border/40 rounded-2xl overflow-hidden"><div className="px-4 py-2 bg-raised/50 border-b border-border text-xs font-medium">{t("order_book")}</div><div className="grid grid-cols-2 divide-x divide-border"><div className="p-3"><div className="text-[10px] text-up font-medium mb-2">{t("bid_side")}</div><div className="flex justify-between text-xs font-mono"><span className="text-up">{snap.buy_price||"—"}</span><span className="text-muted">{snap.buy_volume||"—"}</span></div></div><div className="p-3"><div className="text-[10px] text-down font-medium mb-2">{t("ask_side")}</div><div className="flex justify-between text-xs font-mono"><span className="text-down">{snap.sell_price||"—"}</span><span className="text-muted">{snap.sell_volume||"—"}</span></div></div></div></div>
    </div>
  );
}
