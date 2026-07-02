"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Briefly tints its children green-up / red-down (TW 紅漲綠跌, via --up/--down)
 * when `value` changes between renders — the "price ticked" cue in the live
 * ranking tables. The flash auto-clears after ~600ms. A no-op (just renders
 * children) when the value is unchanged or on first mount, and disabled under
 * prefers-reduced-motion. Keep the tint subtle: it's a hint, not an alarm.
 */
export function FlashValue({
  value,
  className = "",
  children,
}: {
  value: number | null | undefined;
  className?: string;
  children: React.ReactNode;
}) {
  const prev = useRef<number | null | undefined>(value);
  const [dir, setDir] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    const p = prev.current;
    prev.current = value;
    if (p == null || value == null || value === p) return;
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    setDir(value > p ? "up" : "down");
    const id = window.setTimeout(() => setDir(null), 600);
    return () => window.clearTimeout(id);
  }, [value]);

  return (
    <span
      className={`rounded transition-colors duration-500 ${className}`}
      style={dir ? { backgroundColor: dir === "up" ? "color-mix(in srgb, var(--up) 18%, transparent)" : "color-mix(in srgb, var(--down) 18%, transparent)" } : undefined}
    >
      {children}
    </span>
  );
}

/** Small ▲N / ▼N rank-change badge, shown next to the rank number when a row
 *  moved position this update. Fades itself via a CSS animation; renders nothing
 *  when the delta is 0 (no movement). */
export function RankDeltaBadge({ delta }: { delta: number }) {
  if (!delta) return null;
  const up = delta > 0;
  return (
    <span
      className={`ml-0.5 text-[8px] font-mono font-bold animate-rank-delta ${up ? "text-up" : "text-down"}`}
      title={up ? `▲${delta}` : `▼${Math.abs(delta)}`}
    >
      {up ? "▲" : "▼"}{Math.abs(delta)}
    </span>
  );
}
