"use client";

import { useState, useEffect } from "react";

/**
 * Like useState, but persists the value in sessionStorage under `key` so it
 * survives client-side navigation away and back within the same tab/session.
 *
 * Used for UI position state (active tab / sub-tab / view mode) so returning to
 * a page restores where the user left off, instead of resetting to the default.
 * Session-scoped (not localStorage) so a fresh tab/visit starts clean.
 *
 *   const [tab, setTab] = usePersistedState("market.viewTab", 0);
 */
export function usePersistedState<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try {
      const raw = sessionStorage.getItem(key);
      return raw !== null ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* quota / serialization failure — non-fatal, just don't persist */
    }
  }, [key, value]);

  return [value, setValue];
}
