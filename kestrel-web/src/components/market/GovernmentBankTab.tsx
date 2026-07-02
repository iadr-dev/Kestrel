"use client";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { useStockBars } from "@/hooks/useStockBars";
import { daysAgo } from "@/lib/date";
import { StockRowVisual } from "./StockRowVisual";
import { StockSparkline } from "./StockSparkline";

interface GovBankRow {
  stock_id: string;
  date?: string;
  buy_amount?: number;
  sell_amount?: number;
  net_amount?: number;
  net_shares?: number;
  bank_count?: number;
}

export function GovernmentBankTab() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const today = daysAgo(0);
  // Shared id→name map (React Query) — populates reactively even on direct landing.
  const names = useStockNameMap();

  // Per-stock net government-bank buy/sell ranking for the last available day.
  const { data, loading, meta } = useMarketData<GovBankRow>("/institutional/government-bank", { start_date: today });
  const tradeDate = (meta as { trade_date?: string } | undefined)?.trade_date;

  if (loading || !data.length) return (
    <div className="card-atmospheric overflow-hidden h-[350px]">
      <div className="px-4 py-3 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("gov_bank_title")}</span>
      </div>
      <div className="flex-1 flex items-center justify-center h-[280px] text-sm text-muted">
        {loading ? <div className="h-[250px] w-full mx-4 animate-shimmer rounded" /> : t("no_data_non_trading")}
      </div>
    </div>
  );

  // Net amount in 億 (FinMind amounts are in TWD).
  const rows = data.map((r) => ({ ...r, netYi: (r.net_amount || 0) / 1e8 }));
  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.netYi)), 0.01);

  return <GovBankTable rows={rows} maxAbs={maxAbs} names={names} tradeDate={tradeDate} t={t} tm={tm} />;
}

function GovBankTable({
  rows, maxAbs, names, tradeDate, t, tm,
}: {
  rows: (GovBankRow & { netYi: number })[];
  maxAbs: number;
  names: Record<string, string>;
  tradeDate?: string;
  t: (k: string) => string;
  tm: (k: string) => string;
}) {
  // Candle + mini-kline per ranked stock (full shared row visual).
  const bars = useStockBars(rows.map((r) => r.stock_id));

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-4 py-3 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{tm("gov_bank_title")}</span>
        {tradeDate && <span className="text-[10px] text-muted/60">{tradeDate}</span>}
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/30 bg-raised/30">
            <th className="px-4 py-2 text-left text-muted font-medium">{t("stock_id_label")}</th>
            <th className="px-2 py-2 text-center text-muted font-medium hidden sm:table-cell">{t("trend")}</th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("gov_net_buy")} ({t("unit_yi")})</th>
            <th className="px-2 py-2 text-muted font-medium w-[25%]"></th>
            <th className="px-4 py-2 text-right text-muted font-medium">{tm("gov_bank_count")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isUp = row.netYi >= 0;
            const width = (Math.abs(row.netYi) / maxAbs) * 100;
            const bar = bars[row.stock_id];
            return (
              <tr key={row.stock_id} className="border-b border-border/20 hover:bg-raised/20">
                <td className="px-4 py-2.5">
                  <StockRowVisual
                    stock={{ stock_id: row.stock_id, ...bar }}
                    nameMap={names}
                    showSparkline={false}
                  />
                </td>
                <td className="px-2 py-2.5 hidden sm:table-cell">
                  <div className="flex justify-center">
                    {bar?.spark && bar.spark.length >= 2 && <StockSparkline data={bar.spark} />}
                  </div>
                </td>
                <td className={`px-4 py-2.5 text-right font-mono font-bold ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{row.netYi.toFixed(2)}
                </td>
                <td className="px-2 py-2.5">
                  <div className="h-2 bg-raised rounded-full overflow-hidden flex" style={{ flexDirection: isUp ? "row" : "row-reverse" }}>
                    <div className={`h-full rounded-full ${isUp ? "bg-up/70" : "bg-down/70"}`} style={{ width: `${width}%` }} />
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-muted">{row.bank_count || 0}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
