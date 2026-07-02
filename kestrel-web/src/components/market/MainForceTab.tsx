"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { daysAgo } from "@/lib/date";
import { useTradingDate } from "@/hooks/useTradingDate";
import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";
import { StockSearchInput } from "./StockSearchInput";
import { TierGate } from "@/components/gating/TierGate";
import { useEntitlements } from "@/hooks/useEntitlements";

interface TradingReport {
  date: string;
  stock_id: string;
  securities_trader: string;
  securities_trader_id: string;
  buy?: number;
  sell?: number;
}

interface DailyBar { date: string; open?: number; max?: number; min?: number; high?: number; low?: number; close?: number; spread?: number }

interface AggReport {
  date: string;
  total_buy?: number;
  total_sell?: number;
  net?: number;
  broker_count_buy?: number;
  broker_count_sell?: number;
  concentration_5d?: number;
  concentration_20d?: number;
}

export function MainForceTab() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  // 主力分點 tracker is a Pro feature — render as a frosted teaser for other tiers.
  const { can: canFeature } = useEntitlements();
  const mainForceLocked = !canFeature("main_force");
  const [subTab, setSubTab] = useState(0);
  const [stockId, setStockId] = useState("2330");
  const monthAgo = daysAgo(30);
  const today = useTradingDate();

  const { data: aggData, loading: aggLoading } = useMarketData<AggReport>("/institutional/trading-daily-report/agg", { stock_id: stockId, start_date: monthAgo, end_date: today });
  const { data: brokerData, loading: brokerLoading } = useMarketData<TradingReport>("/institutional/trading-daily-report", { stock_id: stockId, report_date: today });
  const { data: priceData } = useMarketData<DailyBar>(`/stocks/${stockId}/price`, { start_date: daysAgo(40) });

  // Focused stock's latest OHLC bar + close series for the header candlestick + mini-kline.
  const stockName = useStockNameMap()[stockId] || "";
  const priceRows = [...priceData].filter((r) => Number(r.close) > 0).sort((a, b) => a.date.localeCompare(b.date));
  const lastBar = priceRows[priceRows.length - 1];
  const spark = priceRows.slice(-20).map((r) => Number(r.close));
  const barClose = lastBar ? Number(lastBar.close) : 0;
  const barSpread = lastBar ? Number(lastBar.spread) || 0 : 0;
  const barPrev = barClose - barSpread;
  const barPct = barPrev > 0 ? (barSpread / barPrev) * 100 : 0;
  const barUp = barSpread >= 0;

  const SUB_TABS = [tm("main_force_overview"), t("top_buyers"), t("top_sellers")];

  // Agg data sorted by date
  const aggSorted = [...aggData].sort((a, b) => a.date.localeCompare(b.date));
  const last20 = aggSorted.slice(-20);
  const tableData = [...aggSorted].reverse().slice(0, 10);

  // Chart scaling
  const nets = last20.map((r) => (r.net || 0) / 1000);
  const netMax = Math.max(...nets.map(Math.abs), 1);
  const concVals = last20.map((r) => r.concentration_5d || 0);
  const concMin = Math.min(...concVals);
  const concMax = Math.max(...concVals);
  const concRange = concMax - concMin || 1;

  // Broker data
  const withNet = brokerData.map((r) => ({ ...r, net: (r.buy || 0) - (r.sell || 0) }));
  const topBuyers = [...withNet].sort((a, b) => b.net - a.net).slice(0, 10);
  const topSellers = [...withNet].sort((a, b) => a.net - b.net).slice(0, 10);

  return (
    <TierGate locked={mainForceLocked} mode="teaser" requiredTier="pro">
    <div className="card-atmospheric overflow-hidden">
      {/* Stock search + sub-tabs */}
      <div className="flex items-center gap-3 px-4 pt-4 pb-3 border-b border-border/30">
        <StockSearchInput
          value={stockId}
          onSelect={setStockId}
          placeholder={t("search_id_or_name")}
          className="w-44"
        />
        <div className="flex gap-1">
          {SUB_TABS.map((label, i) => (
            <button
              key={label}
              onClick={() => setSubTab(i)}
              className={`px-3 py-1.5 text-[11px] font-medium rounded-lg transition-colors ${
                subTab === i
                  ? "bg-signal/10 text-signal"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Focused-stock header: candlestick + name + price + mini-kline */}
      {lastBar && (
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/20 bg-raised/20">
          {lastBar.open != null && (lastBar.max ?? lastBar.high) != null && (lastBar.min ?? lastBar.low) != null && (
            <CandlestickCell
              open={Number(lastBar.open)}
              high={Number(lastBar.max ?? lastBar.high)}
              low={Number(lastBar.min ?? lastBar.low)}
              close={barClose}
              width={12}
              height={30}
            />
          )}
          <div className="min-w-0">
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-mono font-bold text-signal">{stockId}</span>
              {stockName && <span className="text-xs text-foreground/70 truncate">{stockName}</span>}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-mono font-semibold">{barClose.toLocaleString()}</span>
              <span className={`text-xs font-mono font-bold ${barUp ? "text-up" : "text-down"}`}>
                {barUp ? "▲" : "▼"} {barUp ? "+" : ""}{barPct.toFixed(2)}%
              </span>
            </div>
          </div>
          {spark.length >= 2 && <div className="ml-auto"><StockSparkline data={spark} width={72} height={28} /></div>}
        </div>
      )}

      {/* Overview: dual-axis chart */}
      {subTab === 0 && (
        <div>
          {aggLoading ? <div className="p-5 animate-shimmer h-[250px]" /> : last20.length > 1 ? (
            <>
              {/* Dual-axis chart: bars = net buy, line = concentration */}
              <div className="px-4 pt-4 pb-2">
                <div className="flex items-center gap-4 mb-2">
                  <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-up" />{t("net")}({t("unit_lot")})</span>
                  <span className="text-[9px] text-muted flex items-center gap-1"><span className="w-3 h-0.5 bg-signal inline-block rounded" />{tm("concentration_5d")}</span>
                </div>
                <div className="relative h-[100px]">
                  {/* Bars */}
                  <div className="absolute inset-0 flex items-center gap-px">
                    {last20.map((row) => {
                      const net = (row.net || 0) / 1000;
                      const isUp = net >= 0;
                      const h = (Math.abs(net) / netMax) * 45;
                      return (
                        <div key={row.date} className="flex-1 flex flex-col items-center h-full justify-center">
                          {isUp ? (
                            <>
                              <div className="flex-1 flex items-end w-full justify-center">
                                <div className="w-full max-w-[7px] rounded-t-sm bg-up" style={{ height: `${h}%` }} />
                              </div>
                              <div className="flex-1" />
                            </>
                          ) : (
                            <>
                              <div className="flex-1" />
                              <div className="flex-1 flex items-start w-full justify-center">
                                <div className="w-full max-w-[7px] rounded-b-sm bg-down opacity-70" style={{ height: `${h}%` }} />
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Concentration line overlay */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 200 100" preserveAspectRatio="none">
                    <polyline
                      points={last20.map((r, i) => {
                        const x = (i / (last20.length - 1)) * 200;
                        const y = 95 - ((r.concentration_5d || 0) - concMin) / concRange * 90;
                        return `${x.toFixed(1)},${y.toFixed(1)}`;
                      }).join(" ")}
                      fill="none"
                      stroke="var(--signal)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              </div>

              {/* Table */}
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-y border-border/30 bg-raised/30">
                    <th className="px-4 py-2 text-left text-muted font-medium">{t("date")}</th>
                    <th className="px-4 py-2 text-right text-muted font-medium">{t("net")}({t("unit_lot")})</th>
                    <th className="px-4 py-2 text-right text-muted font-medium">{tm("broker_diff")}</th>
                    <th className="px-4 py-2 text-right text-muted font-medium">{tm("concentration_5d")}</th>
                    <th className="px-4 py-2 text-right text-muted font-medium">{tm("concentration_20d")}</th>
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((row) => {
                    const net = row.net || 0;
                    const diff = (row.broker_count_buy || 0) - (row.broker_count_sell || 0);
                    return (
                      <tr key={row.date} className="border-b border-border/20 hover:bg-raised/20">
                        <td className="px-4 py-2.5 font-mono text-muted">{row.date.slice(5)}</td>
                        <td className={`px-4 py-2.5 text-right font-mono font-bold ${net >= 0 ? "text-up" : "text-down"}`}>
                          {net >= 0 ? "+" : ""}{(net / 1000).toFixed(1)}K
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono ${diff >= 0 ? "text-up" : "text-down"}`}>
                          {diff >= 0 ? "+" : ""}{diff}
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono ${(row.concentration_5d || 0) >= 0 ? "text-up" : "text-down"}`}>
                          {(row.concentration_5d || 0).toFixed(1)}%
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono ${(row.concentration_20d || 0) >= 0 ? "text-up" : "text-down"}`}>
                          {(row.concentration_20d || 0).toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          ) : (
            <div className="p-8 text-center text-sm text-muted">{t("no_data")}</div>
          )}
        </div>
      )}

      {/* Top Buyers */}
      {subTab === 1 && (
        <BrokerTable data={topBuyers} loading={brokerLoading} t={t} />
      )}

      {/* Top Sellers */}
      {subTab === 2 && (
        <BrokerTable data={topSellers} loading={brokerLoading} t={t} />
      )}
    </div>
    </TierGate>
  );
}

function BrokerTable({ data, loading, t }: { data: { securities_trader: string; buy?: number; sell?: number; net: number }[]; loading: boolean; t: (key: string) => string }) {
  if (loading) return <div className="p-5 animate-shimmer h-[200px]" />;
  if (!data.length) return <div className="p-8 text-center text-sm text-muted">{t("no_main_force")}</div>;

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-border/30 bg-raised/30">
          <th className="px-4 py-2 text-left text-muted font-medium w-6">#</th>
          <th className="px-4 py-2 text-left text-muted font-medium">{t("broker")}</th>
          <th className="px-4 py-2 text-right text-muted font-medium">{t("buy")}({t("unit_lot")})</th>
          <th className="px-4 py-2 text-right text-muted font-medium">{t("sell")}({t("unit_lot")})</th>
          <th className="px-4 py-2 text-right text-muted font-medium">{t("net")}({t("unit_lot")})</th>
        </tr>
      </thead>
      <tbody>
        {data.map((r, i) => (
          <tr key={i} className="border-b border-border/20 hover:bg-raised/20">
            <td className="px-4 py-2.5 font-mono text-muted">{i + 1}</td>
            <td className="px-4 py-2.5 truncate max-w-[120px]">{r.securities_trader}</td>
            <td className="px-4 py-2.5 text-right font-mono text-up">{(r.buy || 0).toLocaleString()}</td>
            <td className="px-4 py-2.5 text-right font-mono text-down">{(r.sell || 0).toLocaleString()}</td>
            <td className={`px-4 py-2.5 text-right font-mono font-bold ${r.net >= 0 ? "text-up" : "text-down"}`}>
              {r.net >= 0 ? "+" : ""}{r.net.toLocaleString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
