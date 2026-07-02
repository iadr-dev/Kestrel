"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { daysAgo } from "@/lib/date";
import { MS } from "@/lib/constants";

interface TickerItem {
  id: string;
  name: string;
  price: string;
  change: string;
  isUp: boolean;
}

const STOCK_NAMES: Record<string, string> = {
  "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2882": "國泰金",
  "0050": "元大50", "3008": "大立光", "2308": "台達電", "2412": "中華電",
  "2881": "富邦金", "2303": "聯電", "3711": "日月光", "2382": "廣達",
  "TAIEX": "加權指數",
};

const FALLBACK_TICKERS: TickerItem[] = [
  { id: "TAIEX", name: "加權指數", price: "—", change: "—", isUp: true },
  { id: "2330", name: "台積電", price: "—", change: "—", isUp: true },
  { id: "2454", name: "聯發科", price: "—", change: "—", isUp: true },
  { id: "2317", name: "鴻海", price: "—", change: "—", isUp: true },
];

export function StockMarquee() {
  const [tickers, setTickers] = useState<TickerItem[]>(FALLBACK_TICKERS);

  const loadMarqueeTickers = useCallback(async () => {
    try {
      const stockIds = ["2330", "2454", "2317", "2882", "0050", "3008", "2308", "2412"];
      const start = daysAgo(7);
      const results: TickerItem[] = [];

      const res = await apiFetch<{ data: { stock_id: string; close: number; spread: number }[] }>(`/stocks/price-limits?start_date=${start}`);
      const priceData = res.data || [];

      for (const sid of stockIds) {
        const row = priceData.find((r) => r.stock_id === sid);
        if (row && row.close > 0) {
          const pct = (row.spread / (row.close - row.spread)) * 100;
          results.push({
            id: sid,
            name: STOCK_NAMES[sid] || sid,
            price: row.close.toLocaleString(),
            change: `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`,
            isUp: pct >= 0,
          });
        }
      }

      if (results.length > 0) setTickers(results);
    } catch { /* keep fallback */ }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadMarqueeTickers();
    const interval = setInterval(loadMarqueeTickers, MS.MINUTE);
    return () => clearInterval(interval);
  }, [loadMarqueeTickers]);

  return (
    <div className="border-b border-border/50 bg-surface/50 overflow-hidden">
      <div className="flex animate-marquee whitespace-nowrap py-2 px-4 pr-14">
        {[...tickers, ...tickers].map((t, i) => (
          <div key={`${t.id}-${i}`} className="inline-flex items-center gap-2 mx-4 shrink-0">
            <span className="text-[11px] font-medium text-foreground/80">{t.name}</span>
            <span className="text-[10px] font-mono text-muted/60">{t.id}</span>
            <span className="text-[11px] font-mono text-muted">{t.price}</span>
            <span className={`text-[11px] font-mono font-medium ${t.isUp ? "text-up" : "text-down"}`}>{t.change}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
