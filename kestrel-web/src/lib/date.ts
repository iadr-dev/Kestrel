/**
 * Date helpers for API query params (YYYY-MM-DD).
 *
 * Centralised so components don't call `Date.now()` / `new Date()` directly in
 * render (impure — flagged by react-hooks/purity and recomputed every render).
 * These are deliberately impure utilities; keep the impurity in one place.
 */

const DAY_MS = 86_400_000;

/** Today's date as `YYYY-MM-DD` (local-to-UTC via toISOString). */
export function today(): string {
  return new Date().toISOString().split("T")[0];
}

/** The date `n` days before today as `YYYY-MM-DD`. */
export function daysAgo(n: number): string {
  return new Date(Date.now() - n * DAY_MS).toISOString().split("T")[0];
}

/** Format an epoch-ms timestamp as local `YYYY-MM-DD HH:mm:ss` (for "updated at"
 *  badges on cron-fed data). Returns "" for falsy input. */
export function formatDateTime(ms: number | null | undefined): string {
  if (!ms) return "";
  const d = new Date(ms);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
