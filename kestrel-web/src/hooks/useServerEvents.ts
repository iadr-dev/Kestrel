"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

/** Which query-key prefixes to invalidate when each server push event arrives.
 *  Invalidation (not refetch) is cheap: React Query only refetches the queries
 *  currently mounted/observed, so an idle tab does nothing. */
const EVENT_INVALIDATIONS: Record<string, string[]> = {
  news_updated: ["/stocks/news/market", "/twse/market/news"],
  scores_refreshed: ["/ai/rankings", "/ai/summary"],
  alert_triggered: ["/alerts", "/alerts/history"],
};

/** Subscribe to the backend push bus (SSE) and refresh affected React Query caches
 *  when server-originated events arrive — so news/scores/alerts update without
 *  polling. One connection per app instance (mount once, in Providers). The browser
 *  EventSource auto-reconnects; we just re-attach listeners.
 *
 *  This complements (does not replace) market-hours polling for live quotes — those
 *  stay on their timers since their upstream source is itself a timer-pull. */
export function useServerEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") return;

    const es = new EventSource(`${API_BASE}/events/stream`);

    const invalidate = (prefixes: string[]) => {
      queryClient.invalidateQueries({
        predicate: (q) => {
          const head = q.queryKey?.[0];
          return typeof head === "string" && prefixes.some((p) => head.startsWith(p));
        },
      });
    };

    const handlers: Array<[string, (e: MessageEvent) => void]> = [];
    for (const [event, prefixes] of Object.entries(EVENT_INVALIDATIONS)) {
      const fn = () => invalidate(prefixes);
      es.addEventListener(event, fn as EventListener);
      handlers.push([event, fn as (e: MessageEvent) => void]);
    }

    return () => {
      handlers.forEach(([event, fn]) => es.removeEventListener(event, fn as EventListener));
      es.close();
    };
  }, [queryClient]);
}
