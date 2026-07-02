"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { useTranslations, useLocale } from "next-intl";
import { Search, X, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useStockUniverse, type StockInfo } from "@/hooks/useStockUniverse";
import { industryName } from "@/lib/industry";

interface ThemeInfo {
  id: string;
  name_zh: string;
  stock_count: number;
}

// Stable empty defaults shared across renders (see the useState/useQuery note).
const EMPTY_STOCKS: StockInfo[] = [];
const EMPTY_THEMES: ThemeInfo[] = [];
const EMPTY_IDS: Set<string> = new Set();

/** Classify a stock into a market badge (US by leading letter, ETF by 00xxxx / type). */
function getStockBadge(stock: StockInfo): { label: string; color: string } {
  const id = stock.stock_id;
  if (/^[A-Z]/.test(id)) return { label: "US", color: "#4285F4" };
  if (id.startsWith("00") && id.length === 6) return { label: "ETF", color: "#8B5CF6" };
  if (stock.type?.includes("ETF")) return { label: "ETF", color: "#8B5CF6" };
  return { label: "TW", color: "#16a34a" };
}

export function StockSearch() {
  const t = useTranslations("market");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockInfo[]>([]);
  // NOTE: use STABLE empty defaults (module-level constants) for the query data —
  // a `= []` default literal is a fresh reference each render while data is still
  // loading, which would make the search effect (dep: allStocks/allThemes) re-run
  // every render → "Maximum update depth exceeded".
  const { data: allStocks = EMPTY_STOCKS } = useStockUniverse();
  const queryClient = useQueryClient();
  const { data: allThemes = EMPTY_THEMES } = useQuery({
    queryKey: queryKeys.themes.list(),
    queryFn: () => apiFetch<{ data: ThemeInfo[] }>("/themes").then((r) => r.data || []),
    staleTime: 30 * 60 * 1000,
  });
  const { data: watchlistIds = EMPTY_IDS } = useQuery({
    queryKey: queryKeys.watchlist.all(),
    queryFn: () => apiFetch<{ data: { items: { stock_id: string }[] }[] }>("/user/watchlist").then((r) => {
      const ids = new Set<string>();
      for (const wl of r.data || []) for (const item of wl.items || []) ids.add(item.stock_id);
      return ids;
    }),
    staleTime: 30 * 60 * 1000,
  });
  const [themeResults, setThemeResults] = useState<ThemeInfo[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [industryResults, setIndustryResults] = useState<{ name: string; count: number }[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Open with ⌘K / Ctrl+K from anywhere; the modal owns Escape-to-close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Focus the input and lock background scroll while the palette is open.
  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prevOverflow; };
  }, [open]);

  const closePalette = useCallback(() => {
    setOpen(false);
    setQuery("");
    setResults([]);
    setThemeResults([]);
    setIndustryResults([]);
    setSelectedIndex(0);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!query.trim()) { setResults([]); setThemeResults([]); setIndustryResults([]); setSelectedIndex(0); return; }
    const timer = setTimeout(() => {
      const q = query.toLowerCase().trim();
      const filtered = allStocks.filter(
        (s) => s.stock_id.toLowerCase().includes(q) || s.stock_name.toLowerCase().includes(q) || (s.industry_category || "").toLowerCase().includes(q)
      );
      // Sort by market preference (prioritize user's preferred market)
      const marketPref = typeof window !== "undefined" ? localStorage.getItem("kestrel_market_pref") || "tw" : "tw";
      const sorted = filtered.sort((a, b) => {
        const aMatch = (marketPref === "us" && a.type === "US") || (marketPref === "tw" && a.type !== "US") ? -1 : 0;
        const bMatch = (marketPref === "us" && b.type === "US") || (marketPref === "tw" && b.type !== "US") ? -1 : 0;
        return aMatch - bMatch;
      });
      setResults(sorted.slice(0, 15));
      // Search themes
      const filteredThemes = allThemes.filter(
        (t) => t.name_zh.toLowerCase().includes(q) || t.id.toLowerCase().includes(q)
      );
      setThemeResults(filteredThemes.slice(0, 5));
      // Search industries (unique industry_category values)
      const industryMap = new Map<string, number>();
      for (const s of allStocks) {
        if (s.industry_category && s.industry_category.toLowerCase().includes(q)) {
          industryMap.set(s.industry_category, (industryMap.get(s.industry_category) || 0) + 1);
        }
      }
      const industries = Array.from(industryMap.entries())
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);
      setIndustryResults(industries);
      setSelectedIndex(0);
    }, 150);
    return () => clearTimeout(timer);
  }, [query, allStocks, allThemes]);

  const handleSelect = useCallback((stockId: string) => {
    closePalette();
    router.push(`/dashboard/stocks/${stockId}`);
  }, [router, closePalette]);

  // Rows render grouped TW → ETF → US. Keyboard nav + highlight must use this
  // SAME display order, or the highlighted row won't match the row Enter selects.
  const orderedResults = [
    ...results.filter((s) => getStockBadge(s).label === "TW"),
    ...results.filter((s) => getStockBadge(s).label === "ETF"),
    ...results.filter((s) => getStockBadge(s).label === "US"),
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIndex((prev) => Math.min(prev + 1, orderedResults.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIndex((prev) => Math.max(prev - 1, 0)); }
    else if (e.key === "Enter" && orderedResults[selectedIndex]) { e.preventDefault(); handleSelect(orderedResults[selectedIndex].stock_id); }
    else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
  };

  const toggleWatchlist = async (e: React.MouseEvent, stockId: string) => {
    e.stopPropagation();
    const inWatchlist = watchlistIds.has(stockId);
    const wlKey = queryKeys.watchlist.all();
    // Optimistically update the shared React Query cache; refetch to reconcile.
    const next = new Set(watchlistIds);
    if (inWatchlist) next.delete(stockId); else next.add(stockId);
    queryClient.setQueryData(wlKey, next);
    try {
      if (inWatchlist) await apiFetch(`/user/watchlist/item/${stockId}`, { method: "DELETE" });
      else await apiFetch("/user/watchlist/item", { method: "POST", body: JSON.stringify({ stock_id: stockId }) });
    } catch {
      queryClient.setQueryData(wlKey, watchlistIds); // roll back
    } finally {
      queryClient.invalidateQueries({ queryKey: wlKey });
    }
  };

  const hasResults = results.length > 0 || themeResults.length > 0 || industryResults.length > 0;

  return (
    <>
      {/* Trigger — looks like a search field, opens the command palette on click. */}
      <button
        onClick={() => setOpen(true)}
        aria-label={t("search_placeholder")}
        className="flex items-center gap-2 w-full px-3 py-2.5 border border-border/40 rounded-2xl bg-background text-left hover:border-signal/40 transition-colors"
      >
        <Search className="w-4 h-4 text-muted/50 shrink-0" />
        <span className="flex-1 text-sm text-muted/40 truncate min-w-0">{t("search_placeholder")}</span>
        <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-muted/50 border border-border/40 rounded">⌘K</kbd>
      </button>

      {/* Command palette — centered modal over a blurred backdrop (only the modal
          stays sharp). Portaled to <body> so nothing can clip or unblur it. */}
      {open && createPortal(
        <div
          className="fixed inset-0 z-[1500] flex items-start justify-center px-4 pt-[12vh] bg-black/40 backdrop-blur-md animate-in fade-in duration-150"
          onClick={closePalette}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl bg-surface border border-border/40 rounded-2xl shadow-2xl shadow-black/30 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
          >
            {/* Search input */}
            <div className="flex items-center gap-2.5 px-4 py-3.5 border-b border-border/30">
              <Search className="w-5 h-5 text-muted/50 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t("search_placeholder")}
                className="flex-1 bg-transparent text-base outline-none placeholder:text-muted/40 min-w-0"
              />
              <button onClick={closePalette} aria-label={t("search_clear")} className="p-1 hover:bg-raised rounded-lg shrink-0">
                <X className="w-4 h-4 text-muted" />
              </button>
            </div>

            {/* Results */}
            <div className="max-h-[55vh] overflow-y-auto">
              {/* Themes section */}
              {themeResults.length > 0 && (
                <div>
                  <div className="px-3 py-1.5 bg-raised/30 border-b border-border/20">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#e87430]">{t("search_section_themes")}</span>
                  </div>
                  {themeResults.map((theme) => (
                    <div
                      key={theme.id}
                      onClick={() => { closePalette(); router.push(`/dashboard/market?view=industry&theme=${theme.id}`); }}
                      className="flex items-center px-3 py-2.5 cursor-pointer hover:bg-raised/50 border-b border-border/10"
                    >
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-foreground">{theme.name_zh}</span>
                        <span className="text-[10px] text-muted ml-2">{theme.stock_count} {t("search_stocks_unit")}</span>
                      </div>
                      <span className="text-[10px] text-muted">→</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Industry section */}
              {industryResults.length > 0 && (
                <div>
                  <div className="px-3 py-1.5 bg-raised/30 border-b border-border/20">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#0ea5e9]">{t("search_section_industry")}</span>
                  </div>
                  {industryResults.map((ind) => (
                    <div
                      key={ind.name}
                      onClick={() => { setQuery(ind.name); inputRef.current?.focus(); }}
                      className="flex items-center px-3 py-2.5 cursor-pointer hover:bg-raised/50 border-b border-border/10"
                    >
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-foreground">{industryName(ind.name, locale)}</span>
                        <span className="text-[10px] text-muted ml-2">{ind.count} {t("search_stocks_unit")}</span>
                      </div>
                      <span className="text-[10px] text-muted">→</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Stock sections */}
              {(() => {
                const twStocks = results.filter((s) => getStockBadge(s).label === "TW");
                const usStocks = results.filter((s) => getStockBadge(s).label === "US");
                const etfStocks = results.filter((s) => getStockBadge(s).label === "ETF");
                let globalIdx = 0;

                const renderSection = (title: string, items: StockInfo[], color: string) => {
                  if (!items.length) return null;
                  return (
                    <div key={title}>
                      <div className="px-3 py-1.5 bg-raised/30 border-b border-border/20">
                        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color }}>{title}</span>
                      </div>
                      {items.map((stock) => {
                        const idx = globalIdx++;
                        const inWatchlist = watchlistIds.has(stock.stock_id);
                        return (
                          <div
                            key={`${stock.stock_id}-${idx}`}
                            onClick={() => handleSelect(stock.stock_id)}
                            className={`flex items-center w-full px-3 py-2.5 text-left transition-colors border-b border-border/10 last:border-0 cursor-pointer ${
                              idx === selectedIndex ? "bg-signal/8" : "hover:bg-raised/50"
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono font-semibold text-signal">{stock.stock_id}</span>
                                <span className="text-sm truncate text-foreground">{stock.stock_name}</span>
                              </div>
                              {stock.industry_category && (
                                <span className="text-[10px] text-muted/60">{industryName(stock.industry_category, locale)}</span>
                              )}
                            </div>
                            <button
                              onClick={(e) => toggleWatchlist(e, stock.stock_id)}
                              className={`p-1.5 rounded-lg transition-colors shrink-0 ml-2 ${
                                inWatchlist ? "text-down hover:bg-down/10" : "text-muted hover:text-signal hover:bg-signal/10"
                              }`}
                            >
                              {inWatchlist ? <Trash2 className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  );
                };

                return (
                  <>
                    {renderSection(t("search_section_tw"), twStocks, "#16a34a")}
                    {renderSection(t("search_section_etf"), etfStocks, "#8B5CF6")}
                    {renderSection(t("search_section_us"), usStocks, "#4285F4")}
                  </>
                );
              })()}

              {/* Empty states */}
              {query.trim() && !hasResults && allStocks.length > 0 && (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm text-muted">{t("no_results")}</p>
                </div>
              )}
              {!query.trim() && (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm text-muted/60">{t("search_placeholder")}</p>
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
