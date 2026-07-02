"use client";

/** Mini close-price sparkline (like the macro strip) — a compact trend glyph for
 *  a stock row. Colored by net direction over the window. Renders nothing when
 *  there aren't at least two points. */
export function StockSparkline({
  data,
  width = 64,
  height = 24,
}: {
  data: number[];
  width?: number;
  height?: number;
}) {
  if (!data || data.length < 2) return <div style={{ width, height }} className="shrink-0" />;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const isUp = data[data.length - 1] >= data[0];
  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * height}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="shrink-0" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
