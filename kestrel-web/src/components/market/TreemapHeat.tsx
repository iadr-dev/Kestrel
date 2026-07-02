"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useMarketData } from "@/hooks/useMarketData";
import { useTradingDate } from "@/hooks/useTradingDate";
import { usePersistedState } from "@/hooks/usePersistedState";
import { SectorStocksModal } from "./SectorStocksModal";


interface SectorIndex {
  date: string;
  stock_id: string;
  price: number;
  sector_name?: string;
}

type TimeRange = "1d" | "1w" | "1m";
type ViewMode = "grid" | "bar";

function getHeatColorHSL(change: number): string {
  const clamped = Math.max(-8, Math.min(8, change));
  const normalized = (clamped + 8) / 16;
  // Green (down) → neutral → Red (up) — Taiwan convention
  // normalized: 0=green(down), 0.5=neutral, 1=red(up)
  const hue = normalized < 0.5
    ? 140 - normalized * 40  // 140→120 (green range)
    : 20 - (normalized - 0.5) * 30; // 20→5 (red/orange range)
  const saturation = Math.abs(normalized - 0.5) * 2 * 65 + 15;
  const lightness = 22 + (1 - Math.abs(normalized - 0.5) * 2) * 18;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function getGlowColor(change: number): string {
  if (change >= 0) return "rgba(255,95,74,0.4)";
  return "rgba(94,232,133,0.4)";
}


interface SectorData {
  id: string;
  change: number;
  volume: number;
}

function HeatCell({
  sector,
  index,
  totalVolume,
  getName,
  onClick,
  isLarge,
}: {
  sector: SectorData;
  index: number;
  totalVolume: number;
  getName: (id: string) => string;
  onClick: () => void;
  isLarge: boolean;
}) {
  const [pulse, setPulse] = useState(false);
  const prevChangeRef = useRef(sector.change);
  const isUp = sector.change >= 0;
  const isBigMove = Math.abs(sector.change) > 3;

  useEffect(() => {
    const prev = prevChangeRef.current;
    if (Math.abs(sector.change - prev) > 0.3) {
      setPulse(true);
      const timer = setTimeout(() => setPulse(false), 600);
      prevChangeRef.current = sector.change;
      return () => clearTimeout(timer);
    }
    prevChangeRef.current = sector.change;
  }, [sector.change]);

  return (
    <div
      onClick={onClick}
      title={`${getName(sector.id)}: ${isUp ? "+" : ""}${sector.change.toFixed(2)}%`}
      className={`${isLarge ? "col-span-2 row-span-2" : ""} rounded-lg flex flex-col items-center justify-center relative overflow-hidden cursor-pointer`}
      style={{
        backgroundColor: getHeatColorHSL(sector.change),
        transition: "background-color 500ms ease-out, transform 300ms ease-out, box-shadow 400ms ease-out",
        transform: pulse ? "scale(1.03)" : "scale(1)",
        boxShadow: pulse ? `0 0 16px 4px ${getGlowColor(sector.change)}` : "0 0 0 0 transparent",
        animationDelay: `${index * 50}ms`,
      }}
    >
      {/* Inner glow for large cells */}
      {isLarge && (
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background: `radial-gradient(ellipse at center, ${isUp ? "rgba(255,95,74,0.25)" : "rgba(94,232,133,0.25)"}, transparent 70%)`,
          }}
        />
      )}

      {/* Breathing pulse for big movers */}
      {isBigMove && (
        <div
          className="absolute inset-0 animate-[breathe_3s_ease-in-out_infinite] rounded-lg"
          style={{ backgroundColor: getGlowColor(sector.change), opacity: 0.08 }}
        />
      )}

      <div className="text-[10px] font-medium text-white/90 truncate px-1 relative z-10 drop-shadow-sm">
        {getName(sector.id)}
      </div>
      <div
        className="text-xs font-mono font-bold relative z-10 drop-shadow-sm tabular-nums"
        style={{ color: isUp ? "#ffb4a9" : "#a8f0c0" }}
      >
        {isUp ? "+" : ""}{sector.change.toFixed(1)}%
      </div>
      {index < 4 && (
        <div className="text-[9px] text-white/40 mt-0.5 relative z-10">
          {((sector.volume / totalVolume) * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

export function TreemapHeat({ fullPage = false }: { fullPage?: boolean }) {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const ta = useTranslations("common.a11y");
  const locale = useLocale();
  const [range, setRange] = usePersistedState<TimeRange>("kestrel_treemap_range", "1d");
  const [view, setView] = usePersistedState<ViewMode>("kestrel_treemap_view", "grid");
  // Clicking a sector opens a modal listing its constituent stocks.
  const [selectedSector, setSelectedSector] = useState<{ id: string; name: string } | null>(null);
  // "查看全部" — show every sector instead of the top-N cap.
  const [seeAll, setSeeAll] = useState(false);

  const today = useTradingDate();
  const weekAgo = (() => { const d = new Date(today); d.setDate(d.getDate() - 7); return d.toISOString().split("T")[0]; })();
  const monthAgo = (() => { const d = new Date(today); d.setDate(d.getDate() - 30); return d.toISOString().split("T")[0]; })();

  // 1d: intraday 5-sec data; 1w/1m: sector-change endpoint
  const { data: intradayData, loading: intradayLoading } = useMarketData<SectorIndex>(
    "/market/indices/5sec", { trade_date: today, locale }
  );
  const { data: rangeData, loading: rangeLoading } = useMarketData<{ stock_id: string; change: number; sector_name?: string }>(
    range !== "1d" ? "/market/indices/sector-change" : "/market/indices/5sec",
    range === "1w" ? { start_date: weekAgo, end_date: today, locale } : range === "1m" ? { start_date: monthAgo, end_date: today, locale } : { trade_date: today, locale }
  );

  const loading = range === "1d" ? intradayLoading : rangeLoading;

  const emptyShell = (
    <div className="card-atmospheric p-5 h-[240px]">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{t("sector_heatmap")}</span>
        <div className="flex gap-1">
          {([["1d", t("heatmap_1d")], ["1w", t("heatmap_1w")], ["1m", t("heatmap_1m")]] as [TimeRange, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setRange(key)}
              className={`px-2 py-0.5 text-[10px] rounded-md transition-all ${
                range === key ? "bg-signal/20 text-signal font-bold" : "text-muted hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="h-[160px] animate-shimmer rounded" />
    </div>
  );

  if (loading) return emptyShell;

  // Build sector data depending on range mode
  let sectors: SectorData[] = [];

  if (range === "1d") {
    if (!intradayData.length) return emptyShell;
    const sectorMap = new Map<string, { first: number; last: number; count: number }>();
    for (const r of intradayData) {
      const e = sectorMap.get(r.stock_id);
      if (!e) sectorMap.set(r.stock_id, { first: r.price, last: r.price, count: 1 });
      else { e.last = r.price; e.count++; }
    }
    sectors = Array.from(sectorMap.entries())
      .map(([id, { first, last, count }]) => ({ id, change: first > 0 ? ((last - first) / first) * 100 : 0, volume: count }))
      .sort((a, b) => b.volume - a.volume)
      .slice(0, seeAll ? undefined : fullPage ? 30 : 12);
  } else {
    if (!rangeData.length) return emptyShell;
    sectors = rangeData
      .map((r) => ({ id: r.stock_id, change: r.change, volume: 1 }))
      .slice(0, seeAll ? undefined : fullPage ? 30 : 12);
  }

  const totalVolume = sectors.reduce((a, b) => a + b.volume, 0);

  const sectorNameMap = new Map<string, string>();
  if (range === "1d") {
    for (const r of intradayData) {
      if (r.sector_name && !sectorNameMap.has(r.stock_id)) sectorNameMap.set(r.stock_id, r.sector_name);
    }
  } else {
    for (const r of rangeData) {
      if (r.sector_name) sectorNameMap.set(r.stock_id, r.sector_name);
    }
  }
  const getName = (id: string) => sectorNameMap.get(id) || id;

  const sortedByChange = [...sectors].sort((a, b) => b.change - a.change);
  const maxAbsChange = Math.max(...sectors.map((s) => Math.abs(s.change)), 1);

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold">{t("sector_heatmap")}</span>
        <div className="flex items-center gap-3">
          {fullPage && (
            <div className="flex gap-1 border border-border/40 rounded-md p-0.5">
              <button onClick={() => setView("grid")} aria-label={ta("grid_view")} className={`px-2 py-0.5 text-[10px] rounded ${view === "grid" ? "bg-signal/20 text-signal" : "text-muted"}`}>▦</button>
              <button onClick={() => setView("bar")} aria-label={ta("bar_view")} className={`px-2 py-0.5 text-[10px] rounded ${view === "bar" ? "bg-signal/20 text-signal" : "text-muted"}`}>▥</button>
            </div>
          )}
          <div className="flex gap-1">
            {([["1d", t("heatmap_1d")], ["1w", t("heatmap_1w")], ["1m", t("heatmap_1m")]] as [TimeRange, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setRange(key)}
                className={`px-2 py-0.5 text-[10px] rounded-md transition-all ${
                  range === key ? "bg-signal/20 text-signal font-bold" : "text-muted hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setSeeAll((v) => !v)}
            className="text-[10px] text-signal hover:underline"
          >
            {seeAll ? tm("collapse") : `${tm("see_all")} ›`}
          </button>
        </div>
      </div>

      {/* Bar chart view */}
      {view === "bar" && fullPage ? (
        <div className="space-y-1.5 max-h-[420px] overflow-y-auto">
          {sortedByChange.map((s) => {
            const isUp = s.change >= 0;
            const width = Math.abs(s.change) / maxAbsChange * 100;
            return (
              <div
                key={s.id}
                onClick={() => setSelectedSector({ id: s.id, name: getName(s.id) })}
                className="flex items-center gap-2 cursor-pointer hover:bg-surface/50 rounded-md px-2 py-1 group"
              >
                <span className="text-[10px] w-20 truncate text-muted group-hover:text-foreground transition-colors">{getName(s.id)}</span>
                <div className="flex-1 h-4 relative">
                  <div
                    className="h-full rounded-sm"
                    style={{
                      width: `${width}%`,
                      backgroundColor: getHeatColorHSL(s.change),
                      marginLeft: isUp ? "50%" : `${50 - width}%`,
                      transition: "width 500ms ease-out, background-color 500ms ease-out, margin-left 500ms ease-out",
                    }}
                  />
                </div>
                <span className={`text-[10px] font-mono w-12 text-right tabular-nums ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "+" : ""}{s.change.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        /* Grid (treemap) view with animations. seeAll drops the fixed row grid for
           an auto-flow grid (scrollable) so every sector is visible. */
        <div className={`grid gap-1 ${
          seeAll
            ? "grid-cols-4 md:grid-cols-6 auto-rows-[64px] max-h-[460px] overflow-y-auto"
            : fullPage ? "grid-cols-5 grid-rows-6 h-[420px]" : "grid-cols-4 grid-rows-3 h-[180px]"
        }`}>
          {sectors.map((s, i) => (
            <HeatCell
              key={s.id}
              sector={s}
              index={i}
              totalVolume={totalVolume}
              getName={getName}
              onClick={() => setSelectedSector({ id: s.id, name: getName(s.id) })}
              isLarge={i < 2}
            />
          ))}
        </div>
      )}

      {selectedSector && (
        <SectorStocksModal
          sectorId={selectedSector.id}
          sectorName={selectedSector.name}
          onClose={() => setSelectedSector(null)}
        />
      )}
    </div>
  );
}
