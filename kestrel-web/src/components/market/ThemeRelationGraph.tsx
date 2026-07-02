"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { StructureMember, RelationEdge } from "@/types";
import { ThemeTierSwimlane } from "./ThemeTierSwimlane";

const GraphCanvas = dynamic(() => import("reagraph").then((m) => m.GraphCanvas), { ssr: false });

interface RawEdge { source?: string; target?: string; from?: string; to?: string; label?: string; type?: string }

const TIER_COLOR: Record<string, string> = {
  upstream: "#22c55e", midstream: "#e8a13a", downstream: "#3b82f6",
};
// Real supply-chain relationship colors (供應/競合/客戶) + faint tier-flow.
const EDGE_COLOR: Record<string, string> = {
  supplies: "#3b82f6", competes: "#ef4444", customer: "#22c55e", tier_flow: "#3f3f46",
};
const TIER_RANK: Record<string, number> = { upstream: 0, midstream: 1, downstream: 2 };

type ViewMode = "cards" | "graph";

/** 關聯網絡 tab. Two views toggled by 卡片欄 / 關係圖:
 *  - cards (default): ThemeTierSwimlane — deterministic 上游→下游 bands with real
 *    supply-chain edges drawn as accent curves. Always reads well, even with no edges.
 *  - graph: the reagraph force-directed network (organic, good for edge-dense themes
 *    like CoWoS). Both share the same real supply_chain_edges data. */
export function ThemeRelationGraph({
  themeId,
  members,
  names,
  onPick,
}: {
  themeId: string;
  members: StructureMember[];
  names: Record<string, string>;
  onPick: (id: string) => void;
}) {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const [mode, setMode] = useState<ViewMode>("cards");

  // Real supply-chain edges for this theme (sparse, used as accents).
  const { data: graph } = useQuery({
    queryKey: queryKeys.themes.supplyChainGraph(themeId),
    queryFn: () => apiFetch<{ edges: RawEdge[] }>(`/themes/supply-chain/graph/${encodeURIComponent(themeId)}`).then((r) => r ?? { edges: [] }),
    staleTime: 30 * 60 * 1000,
  });

  // Normalize raw edges to the swimlane's typed shape.
  const swimlaneEdges = useMemo<RelationEdge[]>(
    () => (graph?.edges || []).map((e) => ({
      source: e.source || e.from || "",
      target: e.target || e.to || "",
      type: e.label || e.type || "supplies",
    })).filter((e) => e.source && e.target),
    [graph],
  );

  const { nodes, edges, realTypes } = useMemo(() => {
    // Cap to the top ~40 members by relevance to keep reagraph snappy.
    const rank = { high: 0, medium: 1, low: 2 } as const;
    const top = [...members].sort((a, b) => rank[a.relevance] - rank[b.relevance]).slice(0, 40);
    const ids = new Set(top.map((m) => m.stock_id));

    const nodeList = top.map((m) => ({
      id: m.stock_id,
      label: `${m.stock_id} ${names[m.stock_id] || ""}`.trim(),
      fill: TIER_COLOR[m.tier] || "#64748b",
      size: m.relevance === "high" ? 18 : m.relevance === "medium" ? 13 : 9,
      data: { tier: m.tier },
    }));

    const edgeList: { id: string; source: string; target: string; fill: string; size?: number }[] = [];

    // 1) Real supply-chain edges (only between shown nodes). Track which relationship
    //    types actually appear so the legend only shows colors that are on screen.
    const realPairs = new Set<string>();
    const realTypes = new Set<string>();
    for (const [i, e] of (graph?.edges || []).entries()) {
      const s = e.source || e.from || "";
      const tgt = e.target || e.to || "";
      if (!ids.has(s) || !ids.has(tgt)) continue;
      const type = e.label || e.type || "supplies";
      realPairs.add(`${s}->${tgt}`);
      realTypes.add(type);
      edgeList.push({ id: `r${i}`, source: s, target: tgt, fill: EDGE_COLOR[type] || "#64748b", size: 2 });
    }

    // 2) Synthesized tier-flow: one representative (highest-relevance) node per tier
    //    per sub_industry, connected upstream→midstream→downstream. Keeps the graph
    //    readable (a few flow lines) instead of an O(n²) mesh.
    const repByTier: Record<string, string> = {};
    for (const tier of ["upstream", "midstream", "downstream"]) {
      const first = top.find((m) => m.tier === tier);
      if (first) repByTier[tier] = first.stock_id;
    }
    const flow = (a: string, b: string, i: number) => {
      if (repByTier[a] && repByTier[b] && !realPairs.has(`${repByTier[a]}->${repByTier[b]}`)) {
        edgeList.push({ id: `f${i}`, source: repByTier[a], target: repByTier[b], fill: EDGE_COLOR.tier_flow, size: 1 });
      }
    };
    flow("upstream", "midstream", 0);
    flow("midstream", "downstream", 1);

    // Also connect each non-representative node to its tier representative (faint),
    // so isolated nodes aren't floating — gives the lane a visual cluster.
    top.forEach((m, i) => {
      const rep = repByTier[m.tier];
      if (rep && rep !== m.stock_id) {
        edgeList.push({ id: `c${i}`, source: rep, target: m.stock_id, fill: EDGE_COLOR.tier_flow, size: 0.5 });
      }
    });

    return { nodes: nodeList, edges: edgeList, realTypes };
  }, [members, graph, names]);

  if (nodes.length === 0) {
    return <div className="h-[420px] flex items-center justify-center text-sm text-muted">{t("no_data")}</div>;
  }

  const VIEWS: { key: ViewMode; label: string }[] = [
    { key: "cards", label: tm("network_card_view") },
    { key: "graph", label: tm("network_graph_view") },
  ];

  return (
    <div>
      {/* 卡片欄 / 關係圖 toggle */}
      <div className="flex justify-center pt-3">
        <div className="inline-flex rounded-lg border border-border/40 bg-raised/40 p-0.5">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setMode(v.key)}
              className={`px-3 py-1 text-[11px] font-medium rounded-md transition-colors ${
                mode === v.key ? "bg-signal/15 text-signal" : "text-muted hover:text-foreground"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {mode === "cards" ? (
        <ThemeTierSwimlane members={members} edges={swimlaneEdges} names={names} onPick={onPick} />
      ) : (
        <div className="relative h-[460px]">
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            edgeArrowPosition="none"
            labelType="all"
            layoutType="forceDirected2d"
            draggable
            onNodeClick={(node: { id: string }) => { if (/^\d{4,5}$/.test(node.id)) onPick(node.id); }}
          />
          {/* Legends — only show a relationship color when that edge type is actually
              on screen (most themes have no supply_chain_edges yet → no colored lines,
              so showing the full 供應/競合/客戶 legend would be misleading). */}
          <div className="absolute top-3 left-3 flex flex-col gap-1.5 bg-surface/85 backdrop-blur-sm px-3 py-2 rounded-lg text-[9px]">
            {realTypes.size > 0 && (
              <div className="flex gap-3">
                {realTypes.has("supplies") && <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLOR.supplies }} />{tm("edge_supply")}</span>}
                {realTypes.has("competes") && <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLOR.competes }} />{tm("edge_compete")}</span>}
                {realTypes.has("customer") && <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLOR.customer }} />{tm("edge_customer")}</span>}
              </div>
            )}
            <div className="flex gap-3">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: TIER_COLOR.upstream }} />{t("tier_upstream")}</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: TIER_COLOR.midstream }} />{t("tier_midstream")}</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: TIER_COLOR.downstream }} />{t("tier_downstream")}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Re-exported for callers that order nodes by tier elsewhere.
export { TIER_RANK };
