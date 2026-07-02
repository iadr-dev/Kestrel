"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

const GraphCanvas = dynamic(
  () => import("reagraph").then((mod) => mod.GraphCanvas),
  { ssr: false }
);

interface Relationship {
  from: string;
  from_name: string;
  to: string;
  to_name: string;
  type: "supplies" | "customer" | "competes";
  confidence: string;
  revenue_pct: number | null;
}

const TYPE_COLORS: Record<string, string> = {
  supplies: "#e87430",
  customer: "#22c55e",
  competes: "#ef4444",
};


export function SupplyChainGraph({ stockId }: { stockId: string }) {
  const t = useTranslations("data");

  const { data: relationships = [], isLoading: loading } = useQuery({
    queryKey: queryKeys.themes.supplyChain(stockId),
    queryFn: () => apiFetch<{ data: Relationship[] }>(`/themes/supply-chain/stock/${stockId}`).then(r => r.data || []),
    staleTime: 60 * 60 * 1000,
  });

  const edgeLabelMap: Record<string, string> = useMemo(() => ({
    supplies: t("supply_supplies"),
    customer: t("supply_customer"),
    competes: t("supply_competes"),
  }), [t]);

  const { nodes, edges } = useMemo(() => {
    if (!relationships.length) return { nodes: [], edges: [] };

    const nodeMap = new Map<string, { id: string; label: string; isCentral: boolean }>();
    nodeMap.set(stockId, { id: stockId, label: stockId, isCentral: true });

    const edgeList: { id: string; source: string; target: string; label: string; fill: string }[] = [];

    for (const r of relationships) {
      if (r.from === stockId) {
        nodeMap.set(stockId, { id: stockId, label: r.from_name, isCentral: true });
        if (!nodeMap.has(r.to)) nodeMap.set(r.to, { id: r.to, label: r.to_name, isCentral: false });
        edgeList.push({
          id: `${r.from}-${r.to}-${r.type}`,
          source: r.from,
          target: r.to,
          label: edgeLabelMap[r.type] || r.type,
          fill: TYPE_COLORS[r.type] || "#888",
        });
      } else if (r.to === stockId) {
        nodeMap.set(stockId, { id: stockId, label: r.to_name, isCentral: true });
        if (!nodeMap.has(r.from)) nodeMap.set(r.from, { id: r.from, label: r.from_name, isCentral: false });
        edgeList.push({
          id: `${r.from}-${r.to}-${r.type}`,
          source: r.from,
          target: r.to,
          label: edgeLabelMap[r.type] || r.type,
          fill: TYPE_COLORS[r.type] || "#888",
        });
      }
    }

    const nodeList = Array.from(nodeMap.values()).map((n) => ({
      id: n.id,
      label: `${n.label}\n${n.id}`,
      fill: n.isCentral ? "#e87430" : "#64748b",
      size: n.isCentral ? 30 : 20,
    }));

    return { nodes: nodeList, edges: edgeList };
  }, [relationships, stockId, edgeLabelMap]);

  if (loading) return <div className="card-atmospheric p-5 h-[300px] animate-shimmer" />;

  if (!relationships.length) {
    return (
      <div className="card-atmospheric p-5 h-[200px] flex items-center justify-center">
        <span className="text-sm text-muted">{t("supply_no_data")}</span>
      </div>
    );
  }

  return (
    <div className="card-atmospheric p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold">{t("supply_chain")}</h3>
          <p className="text-[10px] text-muted">{t("supply_chain_desc")}</p>
        </div>
        <div className="flex gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#e87430]" />{t("supply_supplies")}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#22c55e]" />{t("supply_customer")}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#ef4444]" />{t("supply_competes")}</span>
        </div>
      </div>

      <div className="h-[350px] rounded-xl overflow-hidden bg-background/50">
        <GraphCanvas
          nodes={nodes}
          edges={edges}
          edgeArrowPosition="end"
          labelType="all"
          layoutType="forceDirected2d"
          draggable
          cameraMode="pan"
        />
      </div>
    </div>
  );
}
