"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { StructureMember, RelationEdge } from "@/types";

export type { RelationEdge };

const TIER_ORDER: StructureMember["tier"][] = ["upstream", "midstream", "downstream"];
const TIER_ACCENT: Record<string, string> = {
  upstream: "#22c55e", midstream: "#e8a13a", downstream: "#3b82f6",
};
const EDGE_COLOR: Record<string, string> = {
  supplies: "#3b82f6", customer: "#22c55e", competes: "#ef4444",
};
const RELEVANCE_RANK: Record<StructureMember["relevance"], number> = { high: 0, medium: 1, low: 2 };

interface Pt { x: number; y: number }

/** 關聯網絡 卡片欄 — a deterministic tier swimlane. Members are laid out in three
 *  horizontal bands (上游→中游→下游); within a band they cluster by sub-industry.
 *  Vertical position therefore encodes supply-chain depth (the thing the view is
 *  meant to teach), unlike a force-directed hairball. Real typed supply-chain
 *  edges are drawn as colored bezier curves on top (供應 blue / 客戶 green /
 *  競合 red) and animate in; when a theme has no edges the bands still read as a
 *  clean role map. Hovering a stock highlights only its links. */
export function ThemeTierSwimlane({
  members,
  edges,
  names,
  onPick,
}: {
  members: StructureMember[];
  edges: RelationEdge[];
  names: Record<string, string>;
  onPick: (id: string) => void;
}) {
  const t = useTranslations("data");
  const tm = useTranslations("market");

  const containerRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [centers, setCenters] = useState<Record<string, Pt>>({});
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [hovered, setHovered] = useState<string | null>(null);

  // Cap to the top members by relevance so the DOM stays light on huge themes.
  const shown = useMemo(
    () => [...members].sort((a, b) => RELEVANCE_RANK[a.relevance] - RELEVANCE_RANK[b.relevance]).slice(0, 60),
    [members],
  );
  const shownIds = useMemo(() => new Set(shown.map((m) => m.stock_id)), [shown]);

  // Bands → sub-industry clusters within each band.
  const bands = useMemo(() => {
    return TIER_ORDER.map((tier) => {
      const list = shown.filter((m) => m.tier === tier);
      const clusters = new Map<string, StructureMember[]>();
      for (const m of list) {
        const key = m.sub_industry || "—";
        (clusters.get(key) ?? clusters.set(key, []).get(key)!).push(m);
      }
      return { tier, count: list.length, clusters: [...clusters.entries()] };
    }).filter((b) => b.count > 0);
  }, [shown]);

  // Only edges whose both ends are on screen; track which types actually appear.
  const drawnEdges = useMemo(
    () => edges.filter((e) => shownIds.has(e.source) && shownIds.has(e.target) && e.source !== e.target),
    [edges, shownIds],
  );
  const presentTypes = useMemo(() => new Set(drawnEdges.map((e) => e.type)), [drawnEdges]);

  // Measure card centers relative to the container after layout / on resize, so
  // the SVG overlay can connect specific stock cards.
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const measure = () => {
      const base = container.getBoundingClientRect();
      const next: Record<string, Pt> = {};
      for (const [id, el] of cardRefs.current) {
        const r = el.getBoundingClientRect();
        next[id] = { x: r.left - base.left + r.width / 2, y: r.top - base.top + r.height / 2 };
      }
      setCenters(next);
      setSize({ w: base.width, h: base.height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(container);
    return () => ro.disconnect();
  }, [bands]);

  // Adjacency for hover-highlight.
  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of drawnEdges) {
      (map.get(e.source) ?? map.set(e.source, new Set()).get(e.source)!).add(e.target);
      (map.get(e.target) ?? map.set(e.target, new Set()).get(e.target)!).add(e.source);
    }
    return map;
  }, [drawnEdges]);

  const isDimmed = (id: string) =>
    hovered != null && hovered !== id && !(neighbors.get(hovered)?.has(id) ?? false);

  const setCardRef = (id: string) => (el: HTMLButtonElement | null) => {
    if (el) cardRefs.current.set(id, el);
    else cardRefs.current.delete(id);
  };

  return (
    <div className="p-4">
      <div ref={containerRef} className="relative">
        {/* Edge overlay — drawn behind the cards. */}
        <svg
          className="pointer-events-none absolute inset-0 z-0"
          width={size.w}
          height={size.h}
          aria-hidden
        >
          {drawnEdges.map((e, i) => {
            const a = centers[e.source];
            const b = centers[e.target];
            if (!a || !b) return null;
            const color = EDGE_COLOR[e.type] || "#64748b";
            // Vertical-ish bezier: bow out via mid control points.
            const midY = (a.y + b.y) / 2;
            const d = `M ${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
            const active = hovered == null || e.source === hovered || e.target === hovered;
            return (
              <path
                key={`${e.source}-${e.target}-${i}`}
                d={d}
                fill="none"
                stroke={color}
                strokeWidth={e.type === "competes" ? 1 : 1.5}
                strokeDasharray={e.type === "competes" ? "3 3" : undefined}
                pathLength={100}
                style={{ "--flow-len": 100, opacity: active ? 0.7 : 0.08 } as React.CSSProperties}
                className="flow-line transition-opacity"
              />
            );
          })}
        </svg>

        {/* Tier bands */}
        <div className="relative z-10 space-y-3">
          {bands.map((band) => (
            <div
              key={band.tier}
              className="rounded-xl border border-border/30 bg-raised/20 p-3"
              style={{ borderLeft: `3px solid ${TIER_ACCENT[band.tier]}` }}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold" style={{ color: TIER_ACCENT[band.tier] }}>
                  {t(`tier_${band.tier}`)}
                </span>
                <span className="text-[10px] text-muted">{band.count}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {band.clusters.map(([sub, list]) => (
                  <div key={sub} className="rounded-lg border border-border/20 bg-surface/40 p-2">
                    <div className="mb-1.5 text-[10px] font-medium text-muted truncate max-w-[160px]">{sub}</div>
                    <div className="flex flex-wrap gap-1.5">
                      {list.map((m) => {
                        const prev = (m.close ?? 0) - (m.spread ?? 0);
                        const pct = prev > 0 ? ((m.spread ?? 0) / prev) * 100 : null;
                        const up = (m.spread ?? 0) >= 0;
                        return (
                          <button
                            key={m.stock_id}
                            ref={setCardRef(m.stock_id)}
                            onClick={() => onPick(m.stock_id)}
                            onMouseEnter={() => setHovered(m.stock_id)}
                            onMouseLeave={() => setHovered(null)}
                            className={`rounded-md bg-raised px-2 py-1 text-left transition-all hover:bg-signal/10 ${
                              isDimmed(m.stock_id) ? "opacity-30" : "opacity-100"
                            } ${m.relevance === "high" ? "ring-1 ring-signal/30" : ""}`}
                          >
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[11px] font-bold text-signal">{m.stock_id}</span>
                              <span className="max-w-[64px] truncate text-[10px] text-foreground/70">{names[m.stock_id] || ""}</span>
                            </div>
                            {pct != null && (
                              <div className={`font-mono text-[9px] font-medium ${up ? "text-up" : "text-down"}`}>
                                {up ? "+" : ""}{pct.toFixed(2)}%
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legend + sparse-edge hint */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10px] text-muted">
        {presentTypes.has("supplies") && <Swatch color={EDGE_COLOR.supplies} label={tm("edge_supply")} />}
        {presentTypes.has("customer") && <Swatch color={EDGE_COLOR.customer} label={tm("edge_customer")} />}
        {presentTypes.has("competes") && <Swatch color={EDGE_COLOR.competes} label={tm("edge_compete")} dashed />}
        {drawnEdges.length === 0 && <span className="text-muted/70">{tm("network_no_edges_hint")}</span>}
      </div>
    </div>
  );
}

function Swatch({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <span
        className="h-0.5 w-4 rounded"
        style={dashed ? { backgroundImage: `repeating-linear-gradient(90deg, ${color} 0 3px, transparent 3px 6px)` } : { background: color }}
      />
      {label}
    </span>
  );
}
