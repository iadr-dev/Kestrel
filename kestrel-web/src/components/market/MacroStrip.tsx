"use client";

import { useTranslations } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { daysAgo } from "@/lib/date";
import { FearGreedGaugeCompact } from "./FearGreedGauge";

interface PriceRow {
  date: string;
  close?: number; price?: number; TAIEX?: number; spot_sell?: number; value?: number; fear_greed?: number;
  // yfinance/macro series use capitalized keys (US indices → "Close", gold → "Price").
  Close?: number; Price?: number; Adj_Close?: number;
}

interface StripItem {
  id: string;
  label: string;
  value: number | null;
  changePct: number | null;
  sparkData: number[];
  isFearGreed?: boolean;
}

function MiniSparkline({ data, isUp }: { data: number[]; isUp: boolean }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-[60px] h-[20px]" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StripCard({ item }: { item: StripItem }) {
  const isUp = (item.changePct ?? 0) >= 0;
  return (
    <div className="shrink-0 w-[130px] px-3 py-2 rounded-xl bg-surface/60 border border-border/30 hover:border-signal/20 transition-colors scroll-snap-align-start">
      <div className="text-[9px] text-muted uppercase tracking-wider truncate">{item.label}</div>
      <div className="flex items-baseline gap-1 mt-0.5">
        <span className="text-sm font-mono font-semibold text-foreground">
          {item.value?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}
        </span>
      </div>
      {item.changePct != null && (
        <span className={`text-[10px] font-mono ${isUp ? "text-up" : "text-down"}`}>
          {isUp ? "▲" : "▼"}{Math.abs(item.changePct).toFixed(2)}%
        </span>
      )}
      <div className="mt-1">
        <MiniSparkline data={item.sparkData} isUp={isUp} />
      </div>
    </div>
  );
}

export function MacroStrip() {
  const t = useTranslations("data");

  const monthAgo = daysAgo(30);
  const weekAgo = daysAgo(7);

  const { data: taiexData } = useMarketData<PriceRow>("/market/indices", { trade_date: weekAgo });
  const { data: tpexData } = useMarketData<PriceRow>("/market/total-return", { data_id: "TPEx", start_date: monthAgo });
  const { data: sp500 } = useMarketData<PriceRow>("/international/us/%5EGSPC/price", { start_date: monthAgo });
  const { data: nasdaq } = useMarketData<PriceRow>("/international/us/%5EIXIC/price", { start_date: monthAgo });
  const { data: dow } = useMarketData<PriceRow>("/international/us/%5EDJI/price", { start_date: monthAgo });
  const { data: sox } = useMarketData<PriceRow>("/international/us/%5ESOX/price", { start_date: monthAgo });
  const { data: goldData } = useMarketData<PriceRow>("/macro/gold", { start_date: monthAgo });
  const { data: vixData } = useMarketData<PriceRow>("/international/us/%5EVIX/price", { start_date: monthAgo });
  const { data: usdData } = useMarketData<PriceRow>("/macro/exchange-rate/USD", { start_date: monthAgo });
  const { data: bondData } = useMarketData<PriceRow>("/macro/bonds/United States 10-Year", { start_date: monthAgo });

  const extractItem = (id: string, label: string, data: PriceRow[], valueKey: keyof PriceRow = "close"): StripItem => {
    // Series come from different providers with inconsistent key casing:
    //   US indices → "Close", gold → "Price", TAIEX → "TAIEX", USD → "spot_sell",
    //   bonds → "value". Try the requested key, then every known variant.
    const values = data
      .map((d) => Number(
        d[valueKey] ?? d.close ?? d.Close ?? d.Adj_Close ?? d.price ?? d.Price ??
        d.TAIEX ?? d.spot_sell ?? d.value ?? 0
      ))
      .filter(Boolean);
    const latest = values[values.length - 1] || null;
    const prev = values.length > 1 ? values[values.length - 2] : null;
    const changePct = latest && prev ? ((latest - prev) / prev) * 100 : null;
    return { id, label, value: latest, changePct, sparkData: values.slice(-20) };
  };

  const items: StripItem[] = [
    extractItem("taiex", "TAIEX", taiexData, "TAIEX"),
    extractItem("tpex", "TPEx", tpexData, "price"),
    extractItem("sp500", "S&P 500", sp500, "Close"),
    extractItem("nasdaq", "NASDAQ", nasdaq, "Close"),
    extractItem("dow", "DOW", dow, "Close"),
    extractItem("sox", "SOX", sox, "Close"),
    extractItem("gold", t("gold"), goldData, "Price"),
    extractItem("vix", "VIX", vixData, "Close"),
    extractItem("usd", "USD/TWD", usdData, "spot_sell"),
    extractItem("us10y", "US 10Y", bondData, "value"),
  ];

  // Auto-scrolling marquee: render the row twice and translate -50% so the loop
  // is seamless. `.animate-marquee` (globals.css) pauses on hover, so resting the
  // cursor on the strip stops it; leaving resumes. `items-stretch` lets the F&G
  // gauge match the macro cards' height exactly.
  const row = (ariaHidden: boolean) => (
    <div className="flex items-stretch gap-2 shrink-0 pr-2" aria-hidden={ariaHidden}>
      {items.map((item) => (
        <StripCard key={item.id} item={item} />
      ))}
      <FearGreedGaugeCompact />
    </div>
  );

  return (
    <div className="overflow-hidden py-1 [mask-image:linear-gradient(to_right,transparent,black_2%,black_98%,transparent)]">
      <div className="flex w-max animate-marquee">
        {row(false)}
        {row(true)}
      </div>
    </div>
  );
}
