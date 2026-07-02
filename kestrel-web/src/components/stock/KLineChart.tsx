"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { createChart, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData, LineData, Time } from "lightweight-charts";
import { MA_COLORS } from "@/lib/chart-colors";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { daysAgo } from "@/lib/date";
import { getLastTradingDate } from "@/hooks/useTradingDate";

interface OHLCVRow {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  Trading_Volume?: number;
  volume?: number;
  max?: number;
  min?: number;
}

type Timeframe = "M5" | "M15" | "H1" | "H4" | "D1" | "W1" | "M1" | "3M" | "1Y";
type Indicator = "volume" | "ma5" | "ma10" | "ma20" | "ma60" | "macd" | "rsi" | "kd" | "bollinger";

const TIMEFRAME_KEYS: { key: Timeframe; i18n: string }[] = [
  { key: "M5", i18n: "tf_5m" },
  { key: "M15", i18n: "tf_15m" },
  { key: "H1", i18n: "tf_1h" },
  { key: "H4", i18n: "tf_4h" },
  { key: "D1", i18n: "tf_daily" },
  { key: "W1", i18n: "tf_weekly" },
  { key: "M1", i18n: "tf_monthly" },
  { key: "3M", i18n: "tf_3m" },
  { key: "1Y", i18n: "tf_1y" },
];

const INDICATORS: { key: Indicator; label: string; disabled?: boolean }[] = [
  { key: "volume", label: "Volume" },
  { key: "ma5", label: "MA5" },
  { key: "ma10", label: "MA10" },
  { key: "ma20", label: "MA20" },
  { key: "ma60", label: "MA60" },
  { key: "bollinger", label: "Bollinger" },
  { key: "macd", label: "MACD", disabled: true },
  { key: "rsi", label: "RSI", disabled: true },
  { key: "kd", label: "KD", disabled: true },
];

export function KLineChart({ stockId, market = "tw" }: { stockId: string; market?: "tw" | "us" }) {
  const t = useTranslations("stock");
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const maSeriesRefs = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  const [timeframe, setTimeframe] = useState<Timeframe>("D1");
  const [activeIndicators, setActiveIndicators] = useState<Set<Indicator>>(new Set(["volume", "ma5", "ma20"]));
  const [showIndicatorPanel, setShowIndicatorPanel] = useState(false);

  // TW uses FinMind's dedicated kbar/week/month endpoints; US uses yfinance's
  // single /history endpoint parameterized by period+interval. The US branch maps
  // each timeframe to the closest yfinance period/interval pair.
  const getKLineParams = (tf: Timeframe) => {
    let endpoint = "";
    const params: Record<string, string> = {};

    if (market === "us") {
      endpoint = `/international/yf/${encodeURIComponent(stockId)}/history`;
      const map: Record<Timeframe, { period: string; interval: string }> = {
        M5: { period: "5d", interval: "5m" },
        M15: { period: "1mo", interval: "15m" },
        H1: { period: "3mo", interval: "1h" },
        H4: { period: "6mo", interval: "1h" },
        D1: { period: "1y", interval: "1d" },
        W1: { period: "2y", interval: "1wk" },
        M1: { period: "5y", interval: "1mo" },
        "3M": { period: "3mo", interval: "1d" },
        "1Y": { period: "1y", interval: "1d" },
      };
      params.period = map[tf].period;
      params.interval = map[tf].interval;
      return { endpoint, params };
    }

    switch (tf) {
      case "M5": case "M15": case "H1": case "H4":
        endpoint = `/stocks/${stockId}/price/kbar`;
        // Last TRADING date, not calendar today — otherwise the intraday kbar
        // request returns empty on weekends / holidays / pre-open (no session).
        params.trade_date = getLastTradingDate();
        break;
      case "D1":
        endpoint = `/stocks/${stockId}/price`;
        params.start_date = daysAgo(365);
        break;
      case "W1":
        endpoint = `/stocks/${stockId}/price/week`;
        params.start_date = daysAgo(365);
        break;
      case "M1":
        endpoint = `/stocks/${stockId}/price/month`;
        params.start_date = daysAgo(730);
        break;
      case "3M":
        endpoint = `/stocks/${stockId}/price`;
        params.start_date = daysAgo(90);
        break;
      case "1Y":
        endpoint = `/stocks/${stockId}/price`;
        params.start_date = daysAgo(365);
        break;
    }
    return { endpoint, params };
  };

  const { endpoint, params: klineParams } = getKLineParams(timeframe);
  const queryString = new URLSearchParams(klineParams).toString();

  const { data: ohlcv = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.kline(`${market}:${stockId}`, timeframe),
    queryFn: () => apiFetch<{ data: Record<string, unknown>[] }>(`${endpoint}?${queryString}`).then(r => (r.data || []).map(normalizeOhlcv)),
    staleTime: 5 * 60 * 1000,
  });

  // Create chart
  useEffect(() => {
    if (!chartContainerRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    // Snapshot the MA-series ref map so cleanup clears the same instance.
    const maSeries = maSeriesRefs.current;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 380,
      layout: { background: { color: "transparent" }, textColor: isDark ? "#6a6155" : "#8a8079", fontSize: 11 },
      grid: { vertLines: { color: isDark ? "#1c1916" : "#f5f2ed" }, horzLines: { color: isDark ? "#1c1916" : "#f5f2ed" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: isDark ? "#2a2520" : "#e8e2d9" },
      timeScale: { borderColor: isDark ? "#2a2520" : "#e8e2d9", timeVisible: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: isDark ? "#ff5f4a" : "#d32f2f",
      downColor: isDark ? "#5ee885" : "#1a9a4a",
      borderUpColor: isDark ? "#ff5f4a" : "#d32f2f",
      borderDownColor: isDark ? "#5ee885" : "#1a9a4a",
      wickUpColor: isDark ? "#ff5f4a" : "#d32f2f",
      wickDownColor: isDark ? "#5ee885" : "#1a9a4a",
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const handleResize = () => {
      if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    return () => { window.removeEventListener("resize", handleResize); chart.remove(); chartRef.current = null; candleSeriesRef.current = null; volumeSeriesRef.current = null; maSeries.clear(); };
  }, []);

  // Update data
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || ohlcv.length === 0) return;

    // Deduplicate and sort by date
    const dedupMap = new Map<string, OHLCVRow>();
    for (const r of ohlcv) {
      if (!dedupMap.has(r.date)) dedupMap.set(r.date, r);
    }
    const uniqueData = Array.from(dedupMap.values()).sort((a, b) => a.date.localeCompare(b.date));

    const candles: CandlestickData<Time>[] = uniqueData.map((r) => ({
      time: r.date as unknown as Time,
      open: r.open,
      high: r.max || r.high,
      low: r.min || r.low,
      close: r.close,
    }));
    candleSeriesRef.current.setData(candles);

    // Volume
    if (activeIndicators.has("volume")) {
      if (!volumeSeriesRef.current) {
        volumeSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
          priceFormat: { type: "volume" },
          priceScaleId: "volume",
        });
        chartRef.current.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      }
      const volData: HistogramData<Time>[] = uniqueData.map((r) => ({
        time: r.date as unknown as Time,
        value: r.Trading_Volume || r.volume || 0,
        color: r.close >= r.open ? "rgba(255,95,74,0.35)" : "rgba(94,232,133,0.35)",
      }));
      volumeSeriesRef.current.setData(volData);
    } else if (volumeSeriesRef.current) {
      chartRef.current.removeSeries(volumeSeriesRef.current);
      volumeSeriesRef.current = null;
    }

    // MA lines
    const maConfigs: { key: Indicator; period: number; color: string }[] = [
      { key: "ma5", period: 5, color: MA_COLORS.ma5 },
      { key: "ma10", period: 10, color: MA_COLORS.ma10 },
      { key: "ma20", period: 20, color: MA_COLORS.ma20 },
      { key: "ma60", period: 60, color: MA_COLORS.ma60 },
    ];

    for (const ma of maConfigs) {
      if (activeIndicators.has(ma.key)) {
        const maData = calculateMA(uniqueData, ma.period);
        let series = maSeriesRefs.current.get(ma.key);
        if (!series) {
          series = chartRef.current.addSeries(LineSeries, { color: ma.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
          maSeriesRefs.current.set(ma.key, series);
        }
        series.setData(maData);
      } else {
        const series = maSeriesRefs.current.get(ma.key);
        if (series) {
          chartRef.current.removeSeries(series);
          maSeriesRefs.current.delete(ma.key);
        }
      }
    }

    // Bollinger Bands (20-period, 2 std dev)
    if (activeIndicators.has("bollinger")) {
      const bbData = calculateBollinger(uniqueData, 20, 2);
      let upperSeries = maSeriesRefs.current.get("bb_upper");
      let lowerSeries = maSeriesRefs.current.get("bb_lower");
      if (!upperSeries) {
        upperSeries = chartRef.current.addSeries(LineSeries, { color: "rgba(138,128,121,0.5)", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
        maSeriesRefs.current.set("bb_upper", upperSeries);
      }
      if (!lowerSeries) {
        lowerSeries = chartRef.current.addSeries(LineSeries, { color: "rgba(138,128,121,0.5)", lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
        maSeriesRefs.current.set("bb_lower", lowerSeries);
      }
      upperSeries.setData(bbData.upper);
      lowerSeries.setData(bbData.lower);
    } else {
      for (const key of ["bb_upper", "bb_lower"]) {
        const s = maSeriesRefs.current.get(key);
        if (s) { chartRef.current.removeSeries(s); maSeriesRefs.current.delete(key); }
      }
    }

    chartRef.current.timeScale().fitContent();
  }, [ohlcv, activeIndicators]);

  const toggleIndicator = (ind: Indicator) => {
    setActiveIndicators((prev) => { const next = new Set(prev); if (next.has(ind)) next.delete(ind); else next.add(ind); return next; });
  };

  return (
    <div className="space-y-3">
      {/* Timeframe selector */}
      <div className="flex items-center gap-1 flex-wrap">
        {TIMEFRAME_KEYS.map((tf) => (
          <button
            key={tf.key}
            onClick={() => setTimeframe(tf.key)}
            className={`px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors ${
              timeframe === tf.key ? "bg-signal/15 text-signal border border-signal/30" : "text-muted hover:text-foreground border border-transparent hover:border-border"
            }`}
          >
            {t(tf.i18n)}
          </button>
        ))}
        <div className="ml-auto">
          <button
            onClick={() => setShowIndicatorPanel(!showIndicatorPanel)}
            className={`px-3 py-1 text-[11px] font-medium rounded-lg border transition-colors ${
              showIndicatorPanel ? "border-signal/30 bg-signal/10 text-signal" : "border-border text-muted hover:text-foreground"
            }`}
          >
            {t("indicators")} ({activeIndicators.size})
          </button>
        </div>
      </div>

      {/* Indicator panel */}
      {showIndicatorPanel && (
        <div className="flex flex-wrap gap-1.5 p-3 bg-raised/50 rounded-xl border border-border/50">
          {INDICATORS.map((ind) => (
            <button
              key={ind.key}
              onClick={() => !ind.disabled && toggleIndicator(ind.key)}
              disabled={ind.disabled}
              className={`px-2.5 py-1 text-[10px] font-medium rounded-lg border transition-colors ${
                ind.disabled ? "text-muted/30 border-border/20 cursor-not-allowed" :
                activeIndicators.has(ind.key) ? "bg-signal/10 text-signal border-signal/30" : "text-muted border-border/50 hover:text-foreground hover:border-border"
              }`}
            >
              {ind.label} {activeIndicators.has(ind.key) && "✓"}
            </button>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="relative rounded-xl overflow-hidden border border-border/50 bg-surface">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/60 z-10">
            <div className="w-5 h-5 border-2 border-signal border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <div ref={chartContainerRef} className="w-full" style={{ height: 380 }} />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 px-1">
        {activeIndicators.has("ma5") && <span className="text-[10px] font-mono" style={{ color: MA_COLORS.ma5 }}>MA5</span>}
        {activeIndicators.has("ma10") && <span className="text-[10px] font-mono" style={{ color: "#ff8c42" }}>MA10</span>}
        {activeIndicators.has("ma20") && <span className="text-[10px] font-mono" style={{ color: "#7dd87d" }}>MA20</span>}
        {activeIndicators.has("ma60") && <span className="text-[10px] font-mono" style={{ color: "#8b5cf6" }}>MA60</span>}
        {activeIndicators.has("bollinger") && <span className="text-[10px] font-mono text-muted">BB(20,2)</span>}
        {activeIndicators.has("volume") && <span className="text-[10px] font-mono text-muted">VOL</span>}
      </div>
    </div>
  );
}

/** Map a raw price row (FinMind lowercase/`max`·`min`, or yfinance capitalized
 *  `Date`/`Open`/`High`/`Low`/`Close`/`Volume`) into the chart's OHLCVRow shape.
 *  yfinance dates carry a time component for intraday bars — lightweight-charts
 *  accepts the full ISO string as `Time`, so we keep it as-is. */
function normalizeOhlcv(r: Record<string, unknown>): OHLCVRow {
  const num = (...vals: unknown[]): number => {
    for (const v of vals) { const n = Number(v); if (Number.isFinite(n)) return n; }
    return 0;
  };
  const rawDate = (r.date ?? r.Date ?? r.Datetime ?? "") as string;
  // Intraday rows look like "2026-06-27 15:30:00" or ISO with "T" — keep the
  // full timestamp so multiple same-day bars don't collapse during dedup.
  const date = String(rawDate);
  return {
    date,
    open: num(r.open, r.Open),
    high: num(r.max, r.high, r.High),
    low: num(r.min, r.low, r.Low),
    close: num(r.close, r.Close),
    Trading_Volume: num(r.Trading_Volume, r.volume, r.Volume),
  };
}

function calculateMA(data: OHLCVRow[], period: number): LineData<Time>[] {
  const result: LineData<Time>[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const slice = data.slice(i - period + 1, i + 1);
    const avg = slice.reduce((sum, r) => sum + r.close, 0) / period;
    result.push({ time: data[i].date as unknown as Time, value: avg });
  }
  return result;
}

function calculateBollinger(data: OHLCVRow[], period: number, stdDev: number): { upper: LineData<Time>[]; lower: LineData<Time>[] } {
  const upper: LineData<Time>[] = [];
  const lower: LineData<Time>[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const slice = data.slice(i - period + 1, i + 1);
    const avg = slice.reduce((sum, r) => sum + r.close, 0) / period;
    const variance = slice.reduce((sum, r) => sum + Math.pow(r.close - avg, 2), 0) / period;
    const std = Math.sqrt(variance);
    upper.push({ time: data[i].date as unknown as Time, value: avg + stdDev * std });
    lower.push({ time: data[i].date as unknown as Time, value: avg - stdDev * std });
  }
  return { upper, lower };
}
