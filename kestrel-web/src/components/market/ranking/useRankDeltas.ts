"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Tracks each item's rank change for the live re-ranking ▲N/▼N badge.
 *
 * Given the currently-ordered list of ids, returns a map of id → rank delta where
 * a POSITIVE delta means the item climbed (moved toward rank 1) and NEGATIVE means
 * it fell. New entries get delta 0 (no badge). Comparison runs in an effect (after
 * commit) — never reading/writing the ref during render — so it's lint-clean and
 * doesn't perturb the render that's drawing the rows.
 */
export function useRankDeltas(orderedIds: string[]): Map<string, number> {
  const prevIndex = useRef<Map<string, number>>(new Map());
  const [deltas, setDeltas] = useState<Map<string, number>>(new Map());
  const key = orderedIds.join(",");

  useEffect(() => {
    const prev = prevIndex.current;
    const next = new Map<string, number>();
    const computed = new Map<string, number>();
    orderedIds.forEach((id, idx) => {
      next.set(id, idx);
      const p = prev.get(id);
      computed.set(id, p === undefined ? 0 : p - idx);
    });
    prevIndex.current = next;
    setDeltas(computed);
    // `key` is the stable string form of orderedIds — re-run only when order changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return deltas;
}
