"use client";
import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { motion } from "framer-motion";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { isTwMarketOpen, isUsMarketOpen } from "@/hooks/useTradingDate";
import { StockRowVisual } from "@/components/market/StockRowVisual";
import { StockSparkline } from "@/components/market/StockSparkline";
import { FlashValue, RankDeltaBadge } from "@/components/market/ranking/FlashValue";
import { useRankDeltas } from "@/components/market/ranking/useRankDeltas";
import {
  MARKET_CONFIGS,
  MARKET_ORDER,
  rowId,
  rowDetailHint,
  filtersKey,
  type ScreenerMarket,
  type ScreenerResultRow,
  type ScreenerColumn,
  type CustomFilter,
} from "./config";
import { CustomFilterSidebar } from "./CustomFilterSidebar";

type Panel = "presets" | "custom";

type ScreenMode = "realtime" | "afterhours";

const SCREENER_STATE_KEY = "kestrel_screener_state";

function readPersistedState(): { market: ScreenerMarket; mode: ScreenMode; active: string | null } {
  const fallback = { market: "tw" as ScreenerMarket, mode: "afterhours" as ScreenMode, active: null };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = sessionStorage.getItem(SCREENER_STATE_KEY);
    if (!raw) return fallback;
    const s = JSON.parse(raw);
    // Back-compat: the old "etf" market == US ETF.
    const m = s.market === "etf" ? "us_etf" : s.market;
    return {
      market: (MARKET_ORDER.includes(m) ? m : "tw") as ScreenerMarket,
      mode: (["realtime", "afterhours"].includes(s.mode) ? s.mode : "afterhours") as ScreenMode,
      active: typeof s.active === "string" ? s.active : null,
    };
  } catch { return fallback; }
}

export default function ScreenerPage() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  const persisted = readPersistedState();
  const [market, setMarket] = useState<ScreenerMarket>(persisted.market);
  const [mode, setMode] = useState<ScreenMode>(persisted.mode);
  const [active, setActive] = useState<string | null>(persisted.active);
  const [today] = useState(() => new Date().toISOString().split("T")[0]);
  const stockNames = useStockNameMap();

  const cfg = MARKET_CONFIGS[market];

  // Presets (curated, fast path) vs Custom (US introspection-generated filter builder).
  // Custom is only available for the yfinance markets (US / US-ETF) — TW screens are
  // fixed DuckDB queries with no per-field threshold API.
  const ts = useTranslations("screener");
  const customAvailable = cfg.source === "yfinance";
  const [panel, setPanel] = useState<Panel>("presets");
  const [customFilters, setCustomFilters] = useState<CustomFilter[]>([]);
  const effectivePanel: Panel = customAvailable ? panel : "presets";

  // Presets per (market, mode). TW/TW-ETF share the DuckDB screen ids; US/US-ETF use
  // the yfinance predefined names (mapped server-side). Phase 4 makes these
  // data-driven from /screener/tw/factors + /yf/screener/presets; for now the curated
  // set lives here and the market tab swaps which set shows.
  const PRESETS: Record<ScreenerMarket, Record<ScreenMode, { id: string; name: string }[]>> = {
    tw: {
      afterhours: [
        { id: "trend", name: t("screen_trend") },
        { id: "ma_reclaim_5", name: t("screen_ma_reclaim_5") },
        { id: "ma_reclaim_10", name: t("screen_ma_reclaim_10") },
        { id: "ma_reclaim_20", name: t("screen_ma_reclaim_20") },
        { id: "ma_reclaim_60", name: t("screen_ma_reclaim_60") },
        { id: "breakout_bollinger", name: t("screen_breakout") },
        { id: "tech_above_rising", name: t("screen_tech_above_rising") },
        { id: "tech_break_20", name: t("screen_tech_break_20") },
        { id: "tech_break_5", name: t("screen_tech_break_5") },
        { id: "tech_slope_20_up", name: t("screen_tech_slope_20_up") },
        { id: "tech_slope_20_down", name: t("screen_tech_slope_20_down") },
        { id: "tech_slope_5_up", name: t("screen_tech_slope_5_up") },
        { id: "tech_slope_5_down", name: t("screen_tech_slope_5_down") },
        { id: "tech_cross_golden", name: t("screen_tech_cross_golden") },
        { id: "tech_cross_death", name: t("screen_tech_cross_death") },
        { id: "tech_long_up", name: t("screen_tech_long_up") },
        { id: "tech_long_down", name: t("screen_tech_long_down") },
        { id: "tech_kd_up", name: t("screen_tech_kd_up") },
        { id: "tech_kd_down", name: t("screen_tech_kd_down") },
        { id: "tech_macd_up", name: t("screen_tech_macd_up") },
        { id: "tech_macd_down", name: t("screen_tech_macd_down") },
        { id: "strong_5d", name: t("screen_strong_5d") },
        { id: "strong_10d", name: t("screen_strong_10d") },
        { id: "surge", name: t("screen_surge") },
        { id: "fund_revyoy_up_3_20", name: t("screen_fund_revyoy_up_3_20") },
        { id: "fund_revyoy_down_3_20", name: t("screen_fund_revyoy_down_3_20") },
        { id: "fund_revmonth_high", name: t("screen_fund_revmonth_high") },
        { id: "fund_revmonth_low", name: t("screen_fund_revmonth_low") },
        { id: "fund_eps_high", name: t("screen_fund_eps_high") },
        { id: "fund_eps_low", name: t("screen_fund_eps_low") },
        { id: "fund_epsyoy_up", name: t("screen_fund_epsyoy_up") },
        { id: "fund_epsyoy_down", name: t("screen_fund_epsyoy_down") },
        { id: "fund_margin_gross_30", name: t("screen_fund_margin_gross_30") },
        { id: "fund_margin_operating_10", name: t("screen_fund_margin_operating_10") },
        { id: "fund_mdecline_gross", name: t("screen_fund_mdecline_gross") },
        { id: "fund_yield_5", name: t("screen_fund_yield_5") },
        { id: "fund_roe_3_20", name: t("screen_fund_roe_3_20") },
        { id: "fund_roa_1_5", name: t("screen_fund_roa_1_5") },
        { id: "fund_debt_30", name: t("screen_fund_debt_30") },
        { id: "fund_quick_150", name: t("screen_fund_quick_150") },
        { id: "institutional_streak", name: t("screen_institutional_streak") },
        { id: "margin_squeeze", name: t("screen_margin_squeeze") },
        { id: "inst_foreign_streak3_buy", name: t("screen_foreign_streak3_buy") },
        { id: "inst_foreign_streak3_sell", name: t("screen_foreign_streak3_sell") },
        { id: "inst_foreign_streak5_buy", name: t("screen_foreign_streak5_buy") },
        { id: "inst_foreign_net3_buy", name: t("screen_foreign_net3_buy") },
        { id: "inst_foreign_net3_sell", name: t("screen_foreign_net3_sell") },
        { id: "inst_trust_streak3_buy", name: t("screen_trust_streak3_buy") },
        { id: "inst_trust_streak3_sell", name: t("screen_trust_streak3_sell") },
        { id: "inst_trust_streak5_buy", name: t("screen_trust_streak5_buy") },
        { id: "inst_trust_net3_buy", name: t("screen_trust_net3_buy") },
        { id: "inst_trust_net3_sell", name: t("screen_trust_net3_sell") },
        { id: "inst_foreign_hold3_buy", name: t("screen_foreign_hold3_buy") },
        { id: "inst_foreign_hold3_sell", name: t("screen_foreign_hold3_sell") },
      ],
      realtime: [
        { id: "volume_spike", name: t("screen_volume_spike") },
        { id: "price_breakout", name: t("screen_price_breakout") },
        { id: "institutional_buy", name: t("screen_institutional_buy") },
      ],
    },
    // TW ETF reuses the same DuckDB technical/momentum screens (ETF ids are numeric and
    // present in price_daily). Chip screens don't apply to ETFs, so keep a focused set.
    tw_etf: {
      afterhours: [
        { id: "trend", name: t("screen_trend") },
        { id: "ma_reclaim_20", name: t("screen_ma_reclaim_20") },
        { id: "ma_reclaim_60", name: t("screen_ma_reclaim_60") },
        { id: "tech_above_rising", name: t("screen_tech_above_rising") },
        { id: "tech_slope_20_up", name: t("screen_tech_slope_20_up") },
        { id: "tech_cross_golden", name: t("screen_tech_cross_golden") },
        { id: "strong_5d", name: t("screen_strong_5d") },
        { id: "surge", name: t("screen_surge") },
        { id: "volume_spike", name: t("screen_volume_spike") },
      ],
      realtime: [
        { id: "volume_spike", name: t("screen_volume_spike") },
        { id: "price_breakout", name: t("screen_price_breakout") },
      ],
    },
    us: {
      afterhours: [
        { id: "us_momentum", name: t("screen_us_momentum") },
        { id: "us_day_gainers", name: t("screen_us_day_gainers") },
        { id: "us_day_losers", name: t("screen_us_day_losers") },
        { id: "us_growth_tech", name: t("screen_us_growth_tech") },
        { id: "us_undervalued_large", name: t("screen_us_undervalued_large") },
        { id: "us_undervalued_growth", name: t("screen_us_undervalued_growth") },
        { id: "us_shorted", name: t("screen_us_shorted") },
        { id: "us_small_cap", name: t("screen_us_small_cap") },
      ],
      realtime: [],
    },
    us_etf: {
      afterhours: [
        { id: "etf_top", name: t("screen_etf_top") },
        { id: "etf_performing", name: t("screen_etf_performing") },
        { id: "etf_tech", name: t("screen_etf_tech") },
        { id: "etf_bond", name: t("screen_etf_bond") },
        { id: "etf_high_dividend", name: t("screen_etf_dividend") },
      ],
      realtime: [],
    },
  };

  const supportsRealtime = cfg.supportsMode;
  const effectiveMode: ScreenMode = supportsRealtime ? mode : "afterhours";
  const currentPresets = PRESETS[market][effectiveMode] || [];

  // Live re-rank gating. Screens are EOD by criteria (the pro pattern); only the
  // intraday-meaningful ones poll live during market hours:
  //   - US / US-ETF: yfinance predefined + custom screens return live regularMarket*
  //     price during US hours → poll when isUsMarketOpen().
  //   - TW: only in 盤中 (realtime) mode AND a price/volume-driven preset (漲跌幅/量/
  //     急漲/爆量), since MA/streak/chip screens are EOD-only. Poll when isTwMarketOpen().
  const TW_INTRADAY_PRESETS = new Set(["volume_spike", "price_breakout", "surge"]);
  const liveUs = cfg.source === "yfinance" && isUsMarketOpen();
  const liveTw = cfg.source === "duckdb" && effectiveMode === "realtime"
    && isTwMarketOpen() && !!active && TW_INTRADAY_PRESETS.has(active);
  const live = liveUs || liveTw;
  const pollMs = live ? 10_000 : false;

  const { data: presetResults = [], isPending: presetPending } = useQuery({
    queryKey: queryKeys.screener.run(market, effectiveMode, active || "", today),
    queryFn: async () => {
      const res = await apiFetch<{ data: ScreenerResultRow[] }>("/screener/run", {
        method: "POST",
        body: JSON.stringify({ screen_type: active, trade_date: today, mode: effectiveMode, market }),
      });
      return res.data || [];
    },
    enabled: effectivePanel === "presets" && !!active,
    refetchInterval: effectivePanel === "presets" ? pollMs : false,
    staleTime: live ? 5_000 : 5 * 60 * 1000,
  });

  // Custom (US/US-ETF) — post the filter list to the yfinance custom screen. The page
  // wraps the leaves in an implicit AND server-side; region defaults to us.
  const { data: customResults = [], isPending: customPending } = useQuery({
    queryKey: queryKeys.screener.custom(cfg.yfQueryType ?? "equity", filtersKey(customFilters), "intradaymarketcap"),
    queryFn: async () => {
      const res = await apiFetch<{ data: ScreenerResultRow[] }>("/international/yf/screen/custom", {
        method: "POST",
        body: JSON.stringify({
          query_type: cfg.yfQueryType ?? "equity",
          filters: customFilters,
          sort_field: "intradaymarketcap",
          sort_asc: false,
          size: 50,
        }),
      });
      return res.data || [];
    },
    enabled: effectivePanel === "custom" && customAvailable && customFilters.length > 0,
    refetchInterval: effectivePanel === "custom" ? pollMs : false,
    staleTime: live ? 5_000 : 5 * 60 * 1000,
  });

  const results = effectivePanel === "custom" ? customResults : presetResults;
  const loading = effectivePanel === "custom"
    ? customPending && customFilters.length > 0
    : presetPending && !!active;

  // Mini-kline series for rows the backend didn't already supply a spark for.
  const [sparks, setSparks] = useState<Record<string, number[]>>({});
  const shownIds = results.slice(0, 30).map(rowId).join(",");
  useEffect(() => {
    const missing = results.slice(0, 30).filter((s) => !(s.spark && s.spark.length >= 2)).map(rowId).filter(Boolean);
    if (missing.length === 0) return;
    let cancelled = false;
    const start = new Date(Date.now() - 40 * 86400000).toISOString().split("T")[0];
    const last20 = (rows: { close?: number; Close?: number }[]) =>
      rows.map((x) => Number(x.close ?? x.Close)).filter((c) => c > 0).slice(-20);

    const load = async (): Promise<Record<string, number[]>> => {
      // US/US-ETF: ONE batched request (per-ticker requests trip the per-IP limiter).
      if (cfg.source === "yfinance") {
        const res = await apiFetch<{ data: Record<string, { close?: number; Close?: number }[]> }>(
          `/international/us/prices/batch?ids=${encodeURIComponent(missing.join(","))}&start_date=${start}`
        ).catch(() => ({ data: {} as Record<string, { close?: number; Close?: number }[]> }));
        const map: Record<string, number[]> = {};
        for (const id of missing) map[id] = last20(res.data?.[id] || []);
        return map;
      }
      // TW/TW-ETF: per-stock DuckDB reads (cheap, not externally rate-limited).
      const pairs = await Promise.all(missing.map((id) =>
        apiFetch<{ data: { close?: number; Close?: number }[] }>(`/stocks/${id}/price?start_date=${start}`)
          .then((r) => [id, last20(r.data || [])] as const)
          .catch(() => [id, [] as number[]] as const)
      ));
      return Object.fromEntries(pairs);
    };

    load().then((map) => { if (!cancelled) setSparks(map); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shownIds, cfg.source]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(SCREENER_STATE_KEY, JSON.stringify({ market, mode, active }));
  }, [market, mode, active]);

  // Keep a valid strategy selected for the current (market, mode).
  useEffect(() => {
    if (!supportsRealtime && mode === "realtime") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode("afterhours");
      return;
    }
    const presets = PRESETS[market][effectiveMode] || [];
    if (presets.length === 0) return;
    const valid = active && presets.some((p) => p.id === active) ? active : presets[0].id;
    if (valid !== active) setActive(valid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [market, mode, supportsRealtime, active]);

  return (
    <div className="h-full flex flex-col p-6">
      {/* Header: market tabs (tw / tw_etf / us / us_etf) */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-1 flex-wrap">
          {MARKET_ORDER.map((key) => (
            <button
              key={key}
              onClick={() => setMarket(key)}
              className={`px-4 py-2 text-sm font-bold rounded-xl transition-all ${
                market === key
                  ? "bg-signal/15 text-signal border border-signal/30"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {tm(MARKET_CONFIGS[key].labelKey)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Presets / Custom toggle — Custom only for yfinance (US/US-ETF) markets */}
          {customAvailable && (
            <div className="flex items-center gap-1 border border-border/40 rounded-xl p-0.5">
              <button
                onClick={() => setPanel("presets")}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  effectivePanel === "presets" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"
                }`}
              >
                {ts("presets")}
              </button>
              <button
                onClick={() => setPanel("custom")}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  effectivePanel === "custom" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"
                }`}
              >
                {ts("custom")}
              </button>
            </div>
          )}

          {/* Mode toggle — TW markets only */}
          {supportsRealtime && (
            <div className="flex items-center gap-1 border border-border/40 rounded-xl p-0.5">
              <button
                onClick={() => { setActive(null); setMode("realtime"); }}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  mode === "realtime" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"
                }`}
              >
                {t("screen_realtime")}
              </button>
              <button
                onClick={() => { setActive(null); setMode("afterhours"); }}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  mode === "afterhours" ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"
                }`}
              >
                {t("screen_afterhours")}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Strategy presets (preset panel only) */}
      {effectivePanel === "presets" && (
        <div className="flex flex-wrap gap-2 mb-6">
          {currentPresets.map((p) => (
            <button
              key={p.id}
              onClick={() => setActive(p.id)}
              className={`px-4 py-2 text-sm rounded-xl border transition-colors ${
                active === p.id
                  ? "border-signal bg-signal/10 text-signal"
                  : "border-border/40 text-muted hover:text-foreground hover:border-border"
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* Body: custom mode shows the filter sidebar + results; preset mode shows results. */}
      <div className="flex-1 min-h-0 flex gap-4">
        {effectivePanel === "custom" && customAvailable && (
          <CustomFilterSidebar
            queryType={cfg.yfQueryType ?? "equity"}
            filters={customFilters}
            onChange={setCustomFilters}
            resultCount={effectivePanel === "custom" && customFilters.length > 0 ? results.length : null}
            loading={loading}
          />
        )}
        <div className="flex-1 min-w-0 overflow-y-auto">
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-12 animate-shimmer rounded-xl" />
            ))}
          </div>
        ) : results.length > 0 ? (
          <ResultsTable
            columns={cfg.columns}
            results={results}
            sparks={sparks}
            stockNames={stockNames}
            live={live}
            t={t}
            tm={tm}
            onRowClick={(r) => router.push(`/dashboard/stocks/${rowId(r)}${rowDetailHint(market)}`)}
          />
        ) : effectivePanel === "custom" ? (
          <div className="card-atmospheric p-10 text-center">
            <p className="text-sm text-muted">{customFilters.length > 0 ? t("no_match") : ts("custom_hint")}</p>
          </div>
        ) : active ? (
          <div className="card-atmospheric p-10 text-center">
            <p className="text-sm text-muted">{t("no_match")}</p>
          </div>
        ) : (
          <div className="card-atmospheric p-10 text-center">
            <p className="text-sm text-muted">{t("select_filter")}</p>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}

function ResultsTable({
  columns, results, sparks, stockNames, live, t, tm, onRowClick,
}: {
  columns: ScreenerColumn[];
  results: ScreenerResultRow[];
  sparks: Record<string, number[]>;
  stockNames: Record<string, string>;
  live: boolean;
  t: ReturnType<typeof useTranslations>;
  tm: ReturnType<typeof useTranslations>;
  onRowClick: (row: ScreenerResultRow) => void;
}) {
  const label = (c: ScreenerColumn) => (c.ns === "market" ? tm(c.labelKey) : t(c.labelKey));
  const shown = results.slice(0, 30);
  // Rank-change deltas (▲N/▼N badge) when live re-ranking.
  const rankDeltas = useRankDeltas(shown.map(rowId));
  // The numeric value behind the price/change cells, for the tick flash.
  const flashVal = (s: ScreenerResultRow, key: string): number | undefined =>
    key === "price" ? s.price ?? s.close : key === "change" ? s.change_pct ?? s.spread : undefined;
  return (
    <div className="border border-border/40 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-raised/50 border-b border-border/30">
        <span className="text-xs text-muted">
          {results.length} {t("matches")}
          {live && <span className="ml-2 inline-flex items-center gap-1 text-up"><span className="w-1.5 h-1.5 rounded-full bg-up animate-pulse" />LIVE</span>}
        </span>
        {results[0]?.trigger_date && (
          <span className="text-[10px] font-mono text-muted">{results[0].trigger_date}</span>
        )}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/20 bg-raised/20">
            <th className="px-4 py-2 text-left text-muted font-medium">{t("stock_id_label")}</th>
            <th className="px-3 py-2 text-center text-muted font-medium">{t("trend")}</th>
            {columns.map((c) => (
              <th key={c.key} className={`px-4 py-2 text-${c.align ?? "right"} text-muted font-medium`}>{label(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((s, i) => {
            const id = rowId(s);
            // Normalize id onto stock_id so the shared row visual + name map work for US too.
            const visual = { ...s, stock_id: id, stock_name: s.stock_name ?? s.name };
            return (
              <motion.tr
                key={id || i}
                layout={live}
                transition={{ type: "spring", stiffness: 600, damping: 40 }}
                onClick={() => onRowClick(s)}
                className="border-b border-border/10 hover:bg-raised/30 cursor-pointer transition-colors"
              >
                <td className="px-4 py-2.5">
                  <div className="flex items-center">
                    <StockRowVisual stock={visual} rank={i + 1} nameMap={stockNames} showSparkline={false} />
                    {live && <RankDeltaBadge delta={rankDeltas.get(id) ?? 0} />}
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex justify-center">
                    <StockSparkline data={(s.spark && s.spark.length >= 2) ? s.spark : (sparks[id] || [])} />
                  </div>
                </td>
                {columns.map((c) => {
                  const v = c.render(s);
                  const isChange = c.key === "change";
                  const up = isChange && !v.startsWith("-") && v !== "—";
                  const flashable = c.key === "price" || c.key === "change";
                  const cls = `px-4 py-2.5 text-${c.align ?? "right"} font-mono ${
                    isChange ? `font-bold ${up ? "text-up" : v === "—" ? "text-muted" : "text-down"}` : "text-foreground"
                  } ${["volume", "market_cap", "net_assets"].includes(c.key) ? "text-muted" : ""}`;
                  return (
                    <td key={c.key} className={cls}>
                      {live && flashable
                        ? <FlashValue value={flashVal(s, c.key)}>{v}</FlashValue>
                        : v}
                    </td>
                  );
                })}
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
