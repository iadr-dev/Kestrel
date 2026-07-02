/**
 * Chart color constants for lightweight-charts and other charting libraries.
 * These are hex strings (required by chart APIs that don't support CSS variables).
 *
 * Follows Kestrel design tokens but as static hex values for chart library compatibility.
 * Update these when globals.css tokens change.
 */

export const CHART_COLORS = {
  light: {
    up: "#b8341c",
    down: "#4a7c59",
    signal: "#e87430",
    legendary: "#d4a017",
    background: "#fffbf4",
    grid: "rgba(139, 115, 85, 0.08)",
    text: "#8b7355",
    crosshair: "#2a1a0e",
  },
  dark: {
    up: "#ff5f4a",
    down: "#5ee885",
    signal: "#ffd83d",
    legendary: "#ffd83d",
    background: "#171412",
    grid: "rgba(255, 255, 255, 0.04)",
    text: "#7a7068",
    crosshair: "#f0e9db",
  },
} as const;

/** Moving average line colors (theme-independent — always same for consistency) */
export const MA_COLORS = {
  ma5: "#ffd83d",
  ma10: "#e87430",
  ma20: "#5ee885",
  ma60: "#8b5cf6",
  ma120: "#ec4899",
  ma240: "#06b6d4",
} as const;

/** Get chart colors based on current theme */
export function getChartColors(isDark: boolean) {
  return isDark ? CHART_COLORS.dark : CHART_COLORS.light;
}
