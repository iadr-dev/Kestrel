/**
 * Locale-aware number formatters for financial data.
 * Units adapt based on locale (億/萬 for zh-TW, B/M/K for en).
 */

export function fmtLargeNumber(v: number | undefined | null, units: { yi: string; wan: string }): string {
  if (!v) return "—";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : v > 0 ? "+" : "";
  if (abs >= 1e8) return `${sign}${(abs / 1e8).toFixed(1)}${units.yi}`;
  if (abs >= 1e4) return `${sign}${(abs / 1e4).toFixed(0)}${units.wan}`;
  return `${sign}${abs.toLocaleString()}`;
}

export function fmtVolume(v: number | undefined | null, units: { yi: string; wan: string }): string {
  if (!v) return "—";
  if (v >= 1e8) return `${(v / 1e8).toFixed(1)}${units.yi}`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(0)}${units.wan}`;
  return v.toLocaleString();
}
