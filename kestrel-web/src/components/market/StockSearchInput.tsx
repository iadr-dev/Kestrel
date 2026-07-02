"use client";

import { useState, useEffect, useRef } from "react";
import { useLocale } from "next-intl";
import { Search } from "lucide-react";
import { useStockUniverse, type StockInfo } from "@/hooks/useStockUniverse";
import { industryName } from "@/lib/industry";

/** Market badge: US by leading letter, ETF by 00xxxx / type, else TW. */
function badge(s: StockInfo): { label: string; color: string } {
  const id = s.stock_id;
  if (/^[A-Za-z]/.test(id)) return { label: "US", color: "#4285F4" };
  if (id.startsWith("00") && id.length === 6) return { label: "ETF", color: "#8B5CF6" };
  if (s.type?.includes("ETF")) return { label: "ETF", color: "#8B5CF6" };
  return { label: "TW", color: "#16a34a" };
}

/** Inline stock search with an autocomplete dropdown — type a code OR name (TW /
 *  ETF / US) and pick a match, mirroring the market command palette but embedded
 *  in a toolbar (no full-screen modal). Calls `onSelect(stock_id)` on choose. */
export function StockSearchInput({
  value,
  onSelect,
  placeholder,
  className = "",
}: {
  value: string;
  onSelect: (stockId: string) => void;
  placeholder?: string;
  className?: string;
}) {
  const { data: universe = [] } = useStockUniverse();
  const locale = useLocale();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  // Close the dropdown on any outside click.
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const q = query.trim().toLowerCase();
  const results = q
    ? universe
        .filter(
          (s) =>
            s.stock_id.toLowerCase().includes(q) ||
            s.stock_name.toLowerCase().includes(q) ||
            (s.industry_category || "").toLowerCase().includes(q)
        )
        // Exact id/name prefix matches first, then the rest.
        .sort((a, b) => {
          const ap = a.stock_id.toLowerCase().startsWith(q) || a.stock_name.toLowerCase().startsWith(q) ? -1 : 0;
          const bp = b.stock_id.toLowerCase().startsWith(q) || b.stock_name.toLowerCase().startsWith(q) ? -1 : 0;
          return ap - bp;
        })
        .slice(0, 8)
    : [];

  const choose = (id: string) => {
    onSelect(id);
    setQuery("");
    setOpen(false);
    setActive(0);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      // Fall back to raw input on Enter (e.g. an exact code the list doesn't have).
      if (e.key === "Enter" && query.trim()) { e.preventDefault(); choose(query.trim().toUpperCase()); }
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((p) => Math.min(p + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((p) => Math.max(p - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(results[active].stock_id); }
    else if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
  };

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <div className="flex items-center gap-1.5 px-2 py-1 bg-surface border border-border/40 rounded-lg focus-within:border-signal/40">
        <Search className="w-3.5 h-3.5 text-muted/50 shrink-0" />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); setActive(0); }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={value ? `${value} · ${placeholder || ""}` : placeholder}
          className="w-full bg-transparent text-xs outline-none placeholder:text-muted/40"
        />
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-72 max-h-72 overflow-y-auto rounded-xl border border-border/40 bg-surface shadow-xl">
          {results.map((s, i) => {
            const b = badge(s);
            return (
              <button
                key={`${s.type}-${s.stock_id}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(s.stock_id)}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left transition-colors ${
                  i === active ? "bg-signal/10" : "hover:bg-raised/50"
                }`}
              >
                <span
                  className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold text-white"
                  style={{ backgroundColor: b.color }}
                >
                  {b.label}
                </span>
                <span className="font-mono text-xs text-signal font-semibold shrink-0">{s.stock_id}</span>
                <span className="text-xs text-foreground/80 truncate">{s.stock_name}</span>
                {s.industry_category && (
                  <span className="ml-auto text-[10px] text-muted/60 truncate max-w-[80px]">{industryName(s.industry_category, locale)}</span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
