"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { X, ChevronRight, Plus, GripVertical } from "lucide-react";
import { DndContext, closestCenter, PointerSensor, TouchSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { apiFetch } from "@/lib/api";
import { mapLimit } from "@/lib/concurrency";
import { normalizeBar } from "@/lib/price";
import { useStockNameMap } from "@/hooks/useStockUniverse";
import { daysAgo } from "@/lib/date";
import type { SnapshotRow, DailyPriceRow } from "@/types";
import { CandlestickCell } from "@/components/market/CandlestickCell";
import { StockSparkline } from "@/components/market/StockSparkline";

interface WatchlistItem {
  stock_id: string;
  note?: string;
}

interface Watchlist {
  id: string;
  name: string;
  items: WatchlistItem[];
}

/** Normalized quote used by the rows: latest price + change vs previous close,
 *  plus the latest OHLC bar (for a candlestick) and a recent close series (mini-kline). */
interface Quote { close: number; spread: number; open?: number; high?: number; low?: number; spark?: number[] }
/** yfinance fast-info (/international/yf/{id}/fast-info). */
interface FastInfo { last_price?: number; previous_close?: number }

const MARKET_TABS = ["TW", "US", "ETF"];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function WatchlistPanel({ open, onClose }: Props) {
  const ta = useTranslations("common.a11y");
  const [tab, setTab] = useState(0);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [addingSection, setAddingSection] = useState(false);
  const [newSectionName, setNewSectionName] = useState("");
  const stockNames = useStockNameMap();
  const [stockPrices, setStockPrices] = useState<Record<string, Quote>>({});

  // Fetch quotes for every watchlist stock. Model (matches Fidelity/IB/TradingView):
  // show the realtime price while the market is open, else the most recent close —
  // never blank.
  //   TW/ETF: FinMind Sponsor realtime snapshot when it has data (intraday);
  //           fall back per-stock to the latest daily close (works after-hours).
  //   US:     yfinance fast-info (last_price live, else previous close) — one call,
  //           covers both states.
  useEffect(() => {
    const allStockIds = watchlists.flatMap((wl) => wl.items.map((i) => i.stock_id));
    if (allStockIds.length === 0) return;
    let cancelled = false;

    const twIds = allStockIds.filter((id) => /^\d/.test(id));   // TW/ETF: numeric codes
    const usIds = allStockIds.filter((id) => /^[A-Za-z]/.test(id));

    const fetchQuotes = async (): Promise<Record<string, Quote>> => {
      const map: Record<string, Quote> = {};

      // --- TW / ETF ---
      if (twIds.length > 0) {
        // 1) Daily price per stock → latest OHLC bar + close series (mini-kline).
        //    Watchlists are small (<30), so per-stock fetches are cheap and give us
        //    the OHLC/series the realtime snapshot lacks.
        await mapLimit(twIds, 6, (id) =>
          apiFetch<{ data: DailyPriceRow[] }>(`/stocks/${id}/price?start_date=${daysAgo(40)}`)
            .then((r) => {
              const rows = (r.data || []).filter((x) => Number(x.close) > 0);
              const last = rows[rows.length - 1];
              if (!last) return;
              const bar = normalizeBar(last);
              map[id] = {
                close: bar.close ?? 0,
                spread: bar.spread ?? 0,
                open: bar.open,
                high: bar.high,
                low: bar.low,
                spark: rows.slice(-20).map((x) => Number(x.close)),
              };
            })
            .catch(() => {})
        );
        // 2) Overlay the realtime snapshot close/change while the market is open
        //    (keeps OHLC+spark from the daily bar, refreshes the live price).
        const snap = await apiFetch<{ data: SnapshotRow[] }>("/stocks/snapshot/all")
          .then((r) => r.data || [])
          .catch(() => [] as SnapshotRow[]);
        const wanted = new Set(twIds);
        for (const r of snap) {
          if (!r.stock_id || !wanted.has(r.stock_id)) continue;
          const close = Number(r.close) || 0;
          if (close > 0) {
            const prev = map[r.stock_id];
            map[r.stock_id] = { ...prev, close, spread: Number(r.change_price) || 0 };
          }
        }
      }

      // --- US ---
      await mapLimit(usIds, 6, async (id) => {
          // Daily price series → OHLC bar + close sparkline (mini-kline). yfinance
          // US series use capitalized keys (Open/High/Low/Close).
          await apiFetch<{ data: DailyPriceRow[] }>(`/international/us/${id}/price?start_date=${daysAgo(40)}`)
            .then((r) => {
              const rows = (r.data || []).filter((x) => Number(x.close ?? x.Close) > 0);
              const last = rows[rows.length - 1];
              if (!last) return;
              const bar = normalizeBar(last);
              map[id] = {
                close: bar.close ?? 0,
                spread: bar.spread ?? 0,
                open: bar.open,
                high: bar.high,
                low: bar.low,
                spark: rows.slice(-20).map((x) => Number(x.close ?? x.Close)),
              };
            })
            .catch(() => {});
          // Overlay live last/prev from fast-info (intraday), keep the series.
          await apiFetch<{ data: FastInfo }>(`/international/yf/${id}/fast-info`)
            .then((r) => {
              const fi = r.data;
              const close = Number(fi?.last_price) || 0;
              const prev = Number(fi?.previous_close) || close;
              if (close > 0) map[id] = { ...map[id], close, spread: close - prev };
            })
            .catch(() => {});
      });

      return map;
    };

    fetchQuotes().then((map) => { if (!cancelled) setStockPrices(map); });
    return () => { cancelled = true; };
  }, [watchlists]);

  const loadWatchlists = useCallback(async () => {
    try {
      const market = MARKET_TABS[tab];
      const res = await apiFetch<{ data: Watchlist[] }>(`/user/watchlist?market=${market}`);
      setWatchlists(res.data || []);
      setExpanded(new Set((res.data || []).map((w: Watchlist) => w.id)));
    } catch { /* silent */ }
  }, [tab]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (open) loadWatchlists();
  }, [open, loadWatchlists]);

  const toggleSection = (id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id); else next.add(id);
    setExpanded(next);
  };

  const removeItem = async (stockId: string) => {
    try {
      await apiFetch(`/user/watchlist/item/${stockId}`, { method: "DELETE" });
      loadWatchlists();
    } catch { /* silent */ }
  };

  const addSection = async () => {
    if (!newSectionName.trim()) return;
    try {
      await apiFetch("/user/watchlist", {
        method: "POST",
        body: JSON.stringify({ name: newSectionName.trim(), market: MARKET_TABS[tab], items: [] }),
      });
      setNewSectionName("");
      setAddingSection(false);
      loadWatchlists();
    } catch { /* silent */ }
  };

  if (!open) return null;

  const totalStocks = watchlists.reduce((a, w) => a + w.items.length, 0);

  return (
    <div className="w-full h-full bg-background flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border min-h-[44px]">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-signal" />
          <h3 className="text-sm font-medium italic">Watchlist</h3>
        </div>
        <button
          onClick={onClose}
          aria-label={ta("close_watchlist")}
          className="w-5 h-5 flex items-center justify-center border border-border rounded text-muted hover:text-foreground transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      {/* Market tabs */}
      <div className="flex border-b border-border">
        {MARKET_TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setTab(i)}
            className={`flex-1 py-2.5 text-[10px] font-mono font-semibold tracking-wider border-b-2 transition-colors ${
              tab === i
                ? "border-signal text-signal bg-surface"
                : "border-transparent text-muted hover:text-foreground"
            } ${i < 2 ? "border-r border-r-border" : ""}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Watchlist sections */}
      <div className="flex-1 overflow-y-auto">
        {watchlists.map((wl) => (
          <WatchlistSection
            key={wl.id}
            wl={wl}
            expanded={expanded.has(wl.id)}
            onToggle={() => toggleSection(wl.id)}
            stockNames={stockNames}
            stockPrices={stockPrices}
            onRemove={removeItem}
            onReorder={(newItems) => {
              setWatchlists((prev) =>
                prev.map((w) => (w.id === wl.id ? { ...w, items: newItems } : w))
              );
            }}
          />
        ))}

        {/* Add section */}
        <div className="px-4 py-3">
          {addingSection ? (
            <div className="flex items-center gap-2">
              <input
                value={newSectionName}
                onChange={(e) => setNewSectionName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") addSection();
                  if (e.key === "Escape") { setAddingSection(false); setNewSectionName(""); }
                }}
                autoFocus
                placeholder="Section name..."
                className="flex-1 min-w-0 px-3 py-2 text-xs bg-surface border border-border/40 rounded-xl outline-none focus:border-signal/50"
              />
              <button
                onClick={addSection}
                className="px-3 py-2 bg-signal text-background text-[10px] font-bold rounded-xl shrink-0"
              >
                ADD
              </button>
            </div>
          ) : (
            <button
              onClick={() => setAddingSection(true)}
              className="w-full py-2.5 border border-dashed border-border rounded text-[10px] font-mono font-semibold tracking-wider text-muted hover:text-foreground hover:border-signal/30 transition-colors"
            >
              <Plus className="w-3 h-3 inline mr-1" />
              NEW SECTOR
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border px-4 py-2 flex items-center justify-between">
        <span className="text-[10px] font-mono text-muted">{totalStocks} positions</span>
        <span className="text-[10px] font-mono text-muted/50">drag to reorder</span>
      </div>
    </div>
  );
}

function WatchlistSection({
  wl, expanded, onToggle, stockNames, stockPrices, onRemove, onReorder,
}: {
  wl: Watchlist;
  expanded: boolean;
  onToggle: () => void;
  stockNames: Record<string, string>;
  stockPrices: Record<string, Quote>;
  onRemove: (id: string) => void;
  onReorder: (items: WatchlistItem[]) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = wl.items.findIndex((i) => i.stock_id === active.id);
    const newIndex = wl.items.findIndex((i) => i.stock_id === over.id);
    if (oldIndex !== -1 && newIndex !== -1) {
      onReorder(arrayMove(wl.items, oldIndex, newIndex));
    }
  };

  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-2 w-full px-4 py-2.5 border-b border-border bg-surface text-[10px] font-mono font-semibold tracking-wider text-muted hover:text-foreground transition-colors"
      >
        <ChevronRight className={`w-3 h-3 transition-transform ${expanded ? "rotate-90" : ""}`} />
        <span className="uppercase">{wl.name}</span>
        <span className="ml-auto text-signal">{wl.items.length}</span>
      </button>

      {expanded && (
        <div>
          {wl.items.length === 0 ? (
            <div className="px-4 py-4 border-b border-border text-center">
              <span className="text-[10px] text-muted/50 font-mono uppercase tracking-wider">Empty — add stocks</span>
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={wl.items.map((i) => i.stock_id)} strategy={verticalListSortingStrategy}>
                {wl.items.map((item) => (
                  <SortableStockRow
                    key={item.stock_id}
                    stockId={item.stock_id}
                    stockName={stockNames[item.stock_id]}
                    price={stockPrices[item.stock_id]}
                    onRemove={() => onRemove(item.stock_id)}
                  />
                ))}
              </SortableContext>
            </DndContext>
          )}
        </div>
      )}
    </div>
  );
}

function SortableStockRow({ stockId, stockName, price, onRemove }: { stockId: string; stockName?: string; price?: Quote; onRemove: () => void }) {
  const ta = useTranslations("common.a11y");
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: stockId });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1, zIndex: isDragging ? 10 : undefined };
  const isUp = price ? price.spread >= 0 : true;
  const changePct = price && price.close > 0 ? ((price.spread / (price.close - price.spread)) * 100).toFixed(2) : null;

  return (
    <div ref={setNodeRef} style={style} className="group flex items-center gap-2 px-4 py-3 border-b border-border/30 hover:bg-surface/50 transition-colors">
      <button {...attributes} {...listeners} aria-label={ta("drag_reorder")} className="cursor-grab active:cursor-grabbing touch-none">
        <GripVertical className="w-3 h-3 text-muted/30 shrink-0" />
      </button>
      {/* Single candlestick (latest OHLC bar) */}
      {price?.open != null && price.high != null && price.low != null ? (
        <CandlestickCell open={price.open} high={price.high} low={price.low} close={price.close} width={10} height={26} />
      ) : (
        <div className="w-2.5 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono font-semibold text-signal">{stockId}</span>
              {stockName && <span className="text-xs text-foreground/70 truncate">{stockName}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-2">
            {/* Mini-kline trend */}
            {price?.spark && price.spark.length >= 2 && <StockSparkline data={price.spark} width={44} height={20} />}
            <div className="text-right">
              <div className="text-xs font-mono font-medium">{price?.close?.toLocaleString() || "—"}</div>
              {changePct && (
                <div className={`text-[10px] font-mono font-medium ${isUp ? "text-up" : "text-down"}`}>
                  {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{changePct}%
                </div>
              )}
            </div>
            {/* Delete button — shows on hover */}
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(); }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-down/10 transition-all"
              aria-label={ta("remove_from_watchlist")}
              title={ta("remove_from_watchlist")}
            >
              <X className="w-3 h-3 text-muted hover:text-down" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
