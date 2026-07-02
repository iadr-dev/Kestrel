"use client";

import { useMemo, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { usePersistedState } from "@/hooks/usePersistedState";
import { useRouter } from "next/navigation";

const GraphCanvas = dynamic(
  () => import("reagraph").then((mod) => mod.GraphCanvas),
  { ssr: false }
);

interface GraphNodeData {
  id: string;
  label: string;
  sub_industry?: string;
  tier?: string;
  stock_count?: number;
}

interface GraphEdgeData {
  from: string;
  to: string;
  type: "supplies" | "technology" | "association";
}

interface ThemeGraphResponse {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

interface Theme {
  id: string;
  name_zh: string;
  name_en: string;
  stock_count: number;
}

const EDGE_COLORS: Record<string, string> = {
  supplies: "#e87430",
  technology: "#6366f1",
  association: "#64748b",
};

const TIER_COLORS: Record<string, string> = {
  upstream: "#22c55e",
  midstream: "#e87430",
  downstream: "#3b82f6",
};

export function IndustryFlowChart() {
  const t = useTranslations("data");
  const tm = useTranslations("market");
  const router = useRouter();
  // Persist the chosen theme (like the other sub-tabs) so it survives navigation.
  const [selectedTheme, setSelectedTheme] = usePersistedState<string | null>("kestrel_industry_flow_theme", null);

  const { data: themes = [], isLoading: themesLoading } = useQuery({
    queryKey: queryKeys.themes.list(),
    queryFn: () => apiFetch<{ data: Theme[] }>("/themes").then(r => r.data || []),
    staleTime: 30 * 60 * 1000,
  });

  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: queryKeys.themes.supplyChainGraph(selectedTheme),
    // React Query forbids a query fn returning undefined — coerce a missing/blank
    // `data` (error envelope, empty response) to null.
    queryFn: () => apiFetch<{ data: ThemeGraphResponse }>(`/themes/supply-chain/graph/${selectedTheme}`).then(r => r.data ?? null),
    staleTime: 30 * 60 * 1000,
    enabled: !!selectedTheme,
  });

  const topThemes = useMemo(
    () => [...themes].sort((a, b) => b.stock_count - a.stock_count).slice(0, 8),
    [themes]
  );

  // Default-select the top theme once themes load (or if the persisted one is gone),
  // so the chart shows data immediately instead of an empty "pick a theme" state.
  useEffect(() => {
    if (topThemes.length === 0) return;
    const valid = selectedTheme && topThemes.some((t) => t.id === selectedTheme);
    if (!valid) setSelectedTheme(topThemes[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topThemes]);

  const { nodes, edges } = useMemo(() => {
    if (!graphData?.nodes?.length) return { nodes: [], edges: [] };

    const nodeList = graphData.nodes.map((n) => ({
      id: n.id,
      label: n.sub_industry || n.label || n.id,
      fill: TIER_COLORS[n.tier || "midstream"] || "#64748b",
      size: Math.max(15, Math.min(40, (n.stock_count || 1) * 3)),
    }));

    const edgeList = graphData.edges.map((e, i) => ({
      id: `edge-${i}`,
      source: e.from,
      target: e.to,
      label: "",
      fill: EDGE_COLORS[e.type] || "#64748b",
    }));

    return { nodes: nodeList, edges: edgeList };
  }, [graphData]);

  if (themesLoading) return (
    <div className="card-atmospheric overflow-hidden h-[400px]">
      <div className="px-5 py-4 border-b border-border/30">
        <span className="text-sm font-semibold">{tm("industry_flow_title")}</span>
      </div>
      <div className="h-[330px] animate-shimmer rounded m-5" />
    </div>
  );

  return (
    <div className="card-atmospheric overflow-hidden">
      <div className="px-5 py-4 border-b border-border/30 flex items-center justify-between">
        <span className="text-sm font-semibold">{tm("industry_flow_title")}</span>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLORS.supplies }} />{tm("edge_supply")}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLORS.technology }} />{tm("edge_tech")}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: EDGE_COLORS.association }} />{tm("edge_assoc")}</span>
        </div>
      </div>

      {/* Theme selector chips */}
      <div className="px-5 py-3 flex gap-2 overflow-x-auto border-b border-border/20">
        {topThemes.map((theme) => (
          <button
            key={theme.id}
            onClick={() => setSelectedTheme(selectedTheme === theme.id ? null : theme.id)}
            className={`shrink-0 px-3 py-1.5 text-[11px] font-medium rounded-lg transition-colors ${
              selectedTheme === theme.id
                ? "bg-signal/15 text-signal border border-signal/30"
                : "text-muted hover:text-foreground border border-border/40"
            }`}
          >
            {theme.name_zh}
          </button>
        ))}
      </div>

      {/* Graph area */}
      {!selectedTheme ? (
        <div className="h-[350px] flex items-center justify-center text-sm text-muted">
          {tm("select_theme_prompt")}
        </div>
      ) : graphLoading ? (
        <div className="h-[350px] animate-shimmer" />
      ) : nodes.length === 0 ? (
        <div className="h-[350px] flex items-center justify-center text-sm text-muted">
          {t("no_data")}
        </div>
      ) : (
        <div className="h-[400px] relative">
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            edgeArrowPosition="end"
            labelType="all"
            layoutType="hierarchicalTd"
            draggable
            cameraMode="pan"
            onNodeClick={(node) => {
              if (node.id && /^\d{4,5}$/.test(node.id)) {
                router.push(`/dashboard/stocks/${node.id}`);
              }
            }}
          />

          {/* Tier legend */}
          <div className="absolute bottom-3 left-3 flex gap-3 text-[9px] bg-surface/80 backdrop-blur-sm px-3 py-1.5 rounded-lg">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full" style={{ background: TIER_COLORS.upstream }} />{t("tier_upstream")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full" style={{ background: TIER_COLORS.midstream }} />{t("tier_midstream")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full" style={{ background: TIER_COLORS.downstream }} />{t("tier_downstream")}</span>
          </div>
        </div>
      )}
    </div>
  );
}
