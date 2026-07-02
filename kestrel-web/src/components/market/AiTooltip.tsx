"use client";

import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface AiSummary {
  stock_id: string;
  position_label?: string;
  summary?: string;
}

interface AiTooltipProps {
  stockId: string;
  children: React.ReactNode;
}

export function AiTooltip({ stockId, children }: AiTooltipProps) {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: summary } = useQuery({
    queryKey: queryKeys.ai.summary(stockId),
    queryFn: () => apiFetch<{ data: AiSummary | null }>(`/ai/summary/${stockId}`).then(r => r.data ?? null),
    staleTime: 60 * 60 * 1000,
    enabled: show,
  });

  const handleEnter = () => {
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };

  const handleLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };

  return (
    <div className="relative inline-flex" onMouseEnter={handleEnter} onMouseLeave={handleLeave}>
      {children}
      {show && summary?.summary && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 rounded-xl bg-surface border border-border/40 shadow-lg pointer-events-none">
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="text-[10px] font-mono text-signal font-bold">{stockId}</span>
            {summary.position_label && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                summary.position_label.includes("多") ? "bg-up/15 text-up" :
                summary.position_label.includes("空") ? "bg-down/15 text-down" :
                "bg-raised text-muted"
              }`}>
                {summary.position_label}
              </span>
            )}
          </div>
          <p className="text-[11px] text-foreground/80 leading-relaxed line-clamp-3">
            {summary.summary}
          </p>
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-surface border-r border-b border-border/40 rotate-45 -mt-1" />
        </div>
      )}
    </div>
  );
}
