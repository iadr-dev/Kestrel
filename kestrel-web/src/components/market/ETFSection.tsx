"use client";
import { useTradingDate } from "@/hooks/useTradingDate";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { daysAgo } from "@/lib/date";
import { normalizeBar } from "@/lib/price";
import type { DailyPriceRow } from "@/types";
import { CandlestickCell } from "./CandlestickCell";
import { StockSparkline } from "./StockSparkline";

/** Latest OHLC bar + recent close series for an ETF row's candlestick + mini-kline. */
interface EtfBar { open?: number; high?: number; low?: number; close?: number; spark: number[] }

interface ETFItem { stock_id: string; stock_name: string; close: number; spread: number; volume: number; date: string; }
interface NavItem { etf_id?: string; name?: string; market_price?: number | string; estimated_nav?: number | string; premium_discount_pct?: number | string; }
interface HoldingItem { [key: string]: string; }
interface PremiumItem { etf_id?: string; name?: string; market_price?: number; estimated_nav?: number; premium_discount_pct?: number; }

export function ETFSection() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  const [view, setView] = useState<"list" | "signal" | "holdings" | "premium">("list");
  const [selectedEtf, setSelectedEtf] = useState<string>("0050");

  const today = useTradingDate();
  const { data: etfs = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.etf.list(today),
    // The scraper feed can deliver close/spread/volume as strings — normalize to
    // numbers once here so all downstream math/formatting/filtering is type-safe.
    queryFn: () => apiFetch<{ data: ETFItem[] }>(`/etf/list?start_date=${today}`).then(r =>
      (r.data || []).map((e) => ({
        ...e,
        close: Number(e.close) || 0,
        spread: Number(e.spread) || 0,
        volume: Number(e.volume) || 0,
      }))
    ),
    staleTime: 10 * 60 * 1000,
  });
  const { data: navData = [] } = useQuery({
    queryKey: queryKeys.etf.nav(),
    queryFn: () => apiFetch<{ data: NavItem[] }>("/etf/nav").then(r => r.data || []),
    staleTime: 30 * 60 * 1000,
    enabled: view === "signal",
  });
  const { data: holdings = [] } = useQuery({
    queryKey: queryKeys.etf.holdings(selectedEtf),
    queryFn: () => apiFetch<{ data: HoldingItem[] }>(`/etf/${selectedEtf}/holdings`).then(r => r.data || []),
    staleTime: 60 * 60 * 1000,
    enabled: view === "holdings",
  });
  const { data: premiumData = [], isLoading: premiumLoading } = useQuery({
    queryKey: queryKeys.etf.premiumDiscount(),
    queryFn: () => apiFetch<{ data: PremiumItem[] }>("/etf/premium-discount?threshold=0.5").then(r => r.data || []),
    staleTime: 10 * 60 * 1000,
    enabled: view === "premium",
  });

  // OHLC bar + close series per listed ETF → candlestick + mini-kline. The scraper
  // list feed has no OHLC/series, so fetch daily price per ETF (only in list view,
  // capped to the rows we render). Keyed on the id set so it refetches on change.
  const [bars, setBars] = useState<Record<string, EtfBar>>({});
  const listIds = view === "list" ? etfs.slice(0, 40).map((e) => e.stock_id).join(",") : "";
  useEffect(() => {
    const ids = listIds ? listIds.split(",") : [];
    if (ids.length === 0) return;
    let cancelled = false;
    Promise.all(ids.map((id) =>
      apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
        .then((r) => {
          const rows = (r.data || []).filter((x) => Number(x.close) > 0);
          const last = rows[rows.length - 1];
          const bar: EtfBar = {
            ...normalizeBar(last),
            spark: rows.slice(-20).map((x) => Number(x.close)),
          };
          return [id, bar] as [string, EtfBar];
        })
        .catch(() => [id, { spark: [] as number[] }] as [string, EtfBar])
    )).then((pairs) => {
      if (cancelled) return;
      const map: Record<string, EtfBar> = {};
      for (const [id, bar] of pairs) map[id] = bar;
      setBars(map);
    });
    return () => { cancelled = true; };
  }, [listIds]);

  // Mini-kline close series per ETF in the 溢折價 view (the premium feed has no
  // price history). Keyed on the id set so it refetches when the list changes.
  const [premiumSparks, setPremiumSparks] = useState<Record<string, number[]>>({});
  const premiumIds = view === "premium" ? premiumData.map((p) => p.etf_id).filter(Boolean).join(",") : "";
  useEffect(() => {
    const ids = premiumIds ? premiumIds.split(",") : [];
    if (ids.length === 0) return;
    let cancelled = false;
    Promise.all(ids.map((id) =>
      apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
        .then((r) => [id, (r.data || []).filter((x) => Number(x.close) > 0).slice(-20).map((x) => Number(x.close))] as [string, number[]])
        .catch(() => [id, [] as number[]] as [string, number[]])
    )).then((pairs) => {
      if (cancelled) return;
      const map: Record<string, number[]> = {};
      for (const [id, s] of pairs) map[id] = s;
      setPremiumSparks(map);
    });
    return () => { cancelled = true; };
  }, [premiumIds]);


  const VIEWS = [
    { key: "list" as const, label: tm("etf_list") },
    { key: "signal" as const, label: tm("etf_signal") },
    { key: "holdings" as const, label: tm("etf_holdings") },
    { key: "premium" as const, label: tm("etf_premium") },
  ];

  return (
    <div className="space-y-6">
      {/* View switcher */}
      <div className="flex justify-center">
        <div className="flex gap-1 bg-surface rounded-2xl p-1 shadow-sm">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={`px-5 py-2 text-xs font-bold rounded-xl transition-all ${
                view === v.key ? "bg-nav-active text-nav-active-text" : "text-muted hover:text-foreground"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* === ETF 列表 === */}
      {view === "list" && (
        <div className="card-atmospheric overflow-hidden">
          <div className="px-5 py-4 flex items-center justify-between border-b border-border/30">
            <span className="text-sm font-semibold">{tm("etf_popular")}</span>
            <span className="text-[10px] text-muted/60">{etfs.length} ETFs</span>
          </div>
          {loading ? (
            <div className="p-5 space-y-3">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 animate-shimmer rounded-xl" />)}</div>
          ) : etfs.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted">{t("no_data")}</div>
          ) : (
            <div className="divide-y divide-border/20">
              {etfs.map((etf, i) => {
                // Scraper feed may send numerics as strings — coerce before math/format.
                const close = Number(etf.close);
                const spread = Number(etf.spread);
                const volume = Number(etf.volume);
                const pct = close && spread ? ((spread / (close - spread)) * 100) : 0;
                const isUp = pct >= 0;
                return (
                  <div
                    key={etf.stock_id}
                    onClick={() => router.push(`/dashboard/stocks/${etf.stock_id}?at=tw-etf`)}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-raised/50 cursor-pointer transition-colors"
                  >
                    <span className="text-[10px] font-mono text-muted/50 w-4">{i + 1}</span>
                    {/* Single candlestick (latest OHLC bar) */}
                    {bars[etf.stock_id]?.open != null && bars[etf.stock_id]?.high != null && bars[etf.stock_id]?.low != null ? (
                      <CandlestickCell open={bars[etf.stock_id].open!} high={bars[etf.stock_id].high!} low={bars[etf.stock_id].low!} close={bars[etf.stock_id].close ?? close} width={11} height={26} />
                    ) : (
                      <div className="w-3 shrink-0" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-semibold text-signal">{etf.stock_id}</span>
                        <span className="text-sm text-foreground/80 truncate">{etf.stock_name}</span>
                      </div>
                    </div>
                    {/* Mini-kline */}
                    <div className="hidden sm:flex justify-center shrink-0">
                      {bars[etf.stock_id]?.spark && bars[etf.stock_id].spark.length >= 2 && (
                        <StockSparkline data={bars[etf.stock_id].spark} width={48} height={20} />
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-mono font-medium">{close > 0 ? close.toLocaleString() : "—"}</div>
                      <div className={`text-[10px] font-mono font-medium ${isUp ? "text-up" : "text-down"}`}>
                        {isUp ? "+" : ""}{pct.toFixed(2)}%
                      </div>
                    </div>
                    <div className="text-right shrink-0 w-16 hidden md:block">
                      <div className="text-[10px] text-muted">{t("volume")}</div>
                      <div className="text-xs font-mono">{volume > 0 ? (volume / 1000000).toFixed(1) + "M" : "—"}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* === 今日訊號 === */}
      {view === "signal" && (
        <div className="space-y-4">
          {/* Flow summary cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="card-atmospheric p-4 border-l-4 border-l-up">
              <div className="text-xs font-bold text-up mb-2">{tm("fund_inflow")}</div>
              <div className="text-lg font-mono font-bold text-up">
                {etfs.length > 0 ? `+${(etfs.filter(e => e.spread > 0).reduce((s, e) => s + (e.volume * e.close / 100000000), 0)).toFixed(1)}${t("unit_yi")}` : "—"}
              </div>
              <div className="text-[10px] text-muted mt-1">{etfs.filter(e => e.spread > 0).length} {tm("up_count")}</div>
            </div>
            <div className="card-atmospheric p-4 border-l-4 border-l-down">
              <div className="text-xs font-bold text-down mb-2">{tm("fund_outflow")}</div>
              <div className="text-lg font-mono font-bold text-down">
                {etfs.length > 0 ? `-${(etfs.filter(e => e.spread < 0).reduce((s, e) => s + Math.abs(e.volume * e.close / 100000000), 0)).toFixed(1)}${t("unit_yi")}` : "—"}
              </div>
              <div className="text-[10px] text-muted mt-1">{etfs.filter(e => e.spread < 0).length} {tm("down_count")}</div>
            </div>
          </div>

          {/* NAV data */}
          <div className="card-atmospheric overflow-hidden">
            <div className="px-5 py-3 border-b border-border/30">
              <span className="text-sm font-semibold">{tm("etf_nav_data")}</span>
            </div>
            {navData.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted">{tm("etf_nav_loading")}</div>
            ) : (
              <div className="divide-y divide-border/20 max-h-[300px] overflow-y-auto">
                {navData.slice(0, 20).map((item, i) => {
                  const pd = Number(item.premium_discount_pct) || 0;
                  const nav = Number(item.estimated_nav);
                  const mkt = Number(item.market_price);
                  return (
                    <div key={item.etf_id || i} className="flex items-center justify-between px-5 py-2.5 text-xs hover:bg-raised/30">
                      <span className="font-mono text-signal w-16">{item.etf_id || ""}</span>
                      <span className="flex-1 text-foreground/80 truncate px-2">{item.name || ""}</span>
                      <span className="font-mono w-16 text-right">{mkt > 0 ? mkt.toFixed(2) : "—"}</span>
                      <span className="font-mono w-16 text-right text-muted">{nav > 0 ? nav.toFixed(2) : "—"}</span>
                      <span className={`font-mono w-16 text-right font-bold ${pd >= 0 ? "text-up" : "text-down"}`}>
                        {pd >= 0 ? "+" : ""}{pd.toFixed(2)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Top movers */}
          <div className="grid grid-cols-2 gap-4">
            <div className="card-atmospheric p-4">
              <div className="text-xs font-semibold mb-3 text-up">{tm("top_gainers")}</div>
              <div className="space-y-2">
                {etfs.filter(e => e.spread > 0).sort((a, b) => (b.spread / (b.close - b.spread)) - (a.spread / (a.close - a.spread))).slice(0, 5).map((e) => (
                  <div key={e.stock_id} className="flex justify-between text-xs">
                    <span className="font-mono text-signal">{e.stock_id}</span>
                    <span className="font-mono text-up">+{((e.spread / (e.close - e.spread)) * 100).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card-atmospheric p-4">
              <div className="text-xs font-semibold mb-3 text-down">{tm("top_losers")}</div>
              <div className="space-y-2">
                {etfs.filter(e => e.spread < 0).sort((a, b) => (a.spread / (a.close - a.spread)) - (b.spread / (b.close - b.spread))).slice(0, 5).map((e) => (
                  <div key={e.stock_id} className="flex justify-between text-xs">
                    <span className="font-mono text-signal">{e.stock_id}</span>
                    <span className="font-mono text-down">{((e.spread / (e.close - e.spread)) * 100).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* === 資金持股 === */}
      {view === "holdings" && (
        <div className="space-y-4">
          {/* ETF selector */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted">ETF:</span>
            <select
              value={selectedEtf}
              onChange={(e) => setSelectedEtf(e.target.value)}
              className="text-xs bg-surface border border-border/40 rounded-xl px-3 py-1.5 outline-none"
            >
              {etfs.slice(0, 10).map((e) => (
                <option key={e.stock_id} value={e.stock_id}>{e.stock_id} {e.stock_name}</option>
              ))}
            </select>
          </div>

          {/* Holdings table */}
          <div className="card-atmospheric overflow-hidden">
            <div className="px-5 py-3 border-b border-border/30">
              <span className="text-sm font-semibold">{selectedEtf} {tm("etf_composition")}</span>
            </div>
            {holdings.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted">{tm("etf_holdings_unavailable")}</div>
            ) : (
              <div className="divide-y divide-border/20 max-h-[400px] overflow-y-auto">
                {holdings.map((item, i) => (
                  <div key={i} className="flex items-center justify-between px-5 py-2.5 text-xs hover:bg-raised/30">
                    {Object.entries(item).filter(([key]) => key !== "date" && key !== "etf_id").slice(0, 4).map(([, v], j) => (
                      <span key={j} className={j === 0 ? "font-mono text-signal min-w-[60px]" : "text-foreground/80"}>{String(v)}</span>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* === 溢折價 === */}
      {view === "premium" && (
        <div className="card-atmospheric overflow-hidden">
          <div className="px-5 py-3 border-b border-border/30">
            <span className="text-sm font-semibold">{tm("etf_premium_title")}</span>
          </div>
          {premiumLoading ? (
            <div className="p-5 animate-shimmer h-[250px]" />
          ) : premiumData.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted">{t("no_data")}</div>
          ) : (
            <>
              <div className="flex items-center px-5 py-2 text-[10px] text-muted border-b border-border/20">
                <span className="w-16">ETF</span>
                <span className="flex-1">{t("stock_id_label")}</span>
                <span className="w-16 text-center hidden sm:block">{t("trend")}</span>
                <span className="w-20 text-right">{tm("etf_nav_label")}</span>
                <span className="w-20 text-right">{t("close")}</span>
                <span className="w-20 text-right">{tm("etf_pd_pct")}</span>
              </div>
              <div className="divide-y divide-border/10 max-h-[350px] overflow-y-auto">
                {premiumData.map((item, i) => {
                  // The API may send these as strings — coerce before formatting so
                  // .toFixed never throws (Number() handles both number and string).
                  const pct = Number(item.premium_discount_pct) || 0;
                  const nav = Number(item.estimated_nav);
                  const mkt = Number(item.market_price);
                  const isPremium = pct > 0;
                  const spark = item.etf_id ? premiumSparks[item.etf_id] : undefined;
                  return (
                    <div key={i} className="flex items-center px-5 py-2.5 hover:bg-raised/30 transition-colors">
                      <span className="w-16 text-xs font-mono text-signal font-bold">{item.etf_id}</span>
                      <span className="flex-1 text-xs truncate text-foreground/70">{item.name}</span>
                      <span className="w-16 hidden sm:flex justify-center">
                        {spark && spark.length >= 2 ? <StockSparkline data={spark} width={48} height={20} /> : null}
                      </span>
                      <span className="w-20 text-right text-xs font-mono">{nav > 0 ? nav.toFixed(2) : "—"}</span>
                      <span className="w-20 text-right text-xs font-mono">{mkt > 0 ? mkt.toFixed(2) : "—"}</span>
                      <span className={`w-20 text-right text-xs font-mono font-bold ${isPremium ? "text-up" : "text-down"}`}>
                        {isPremium ? "+" : ""}{pct.toFixed(2)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
