interface Props {
  data: {
    title?: string;
    chart_type: "bar" | "line" | "area";
    labels: string[];
    values: number[];
    unit?: string;
    color?: string;
  };
}

export function MiniChart({ data }: Props) {
  const { labels, values, chart_type, title, unit } = data;
  if (!values || values.length === 0) return null;

  const max = Math.max(...values.map(Math.abs));
  const width = 280;
  const height = 80;
  const padding = { top: 8, right: 8, bottom: 20, left: 8 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const baseColor = data.color || "var(--signal)";

  const renderBars = () => {
    const barWidth = chartW / values.length * 0.7;
    const gap = chartW / values.length * 0.3;
    return values.map((v, i) => {
      const barH = max > 0 ? (Math.abs(v) / max) * chartH : 0;
      const x = padding.left + i * (barWidth + gap);
      const y = v >= 0 ? padding.top + (chartH - barH) : padding.top + chartH;
      const fill = v >= 0 ? "var(--signal-up)" : "var(--signal-down)";
      return <rect key={i} x={x} y={v >= 0 ? y : padding.top + chartH - barH} width={barWidth} height={barH} rx={2} fill={fill} opacity={0.85} />;
    });
  };

  const renderLine = () => {
    if (values.length < 2) return null;
    const points = values.map((v, i) => {
      const x = padding.left + (i / (values.length - 1)) * chartW;
      const y = max > 0 ? padding.top + chartH - ((v - Math.min(...values)) / (max - Math.min(...values) || 1)) * chartH : padding.top + chartH / 2;
      return `${x},${y}`;
    });
    return (
      <>
        {chart_type === "area" && (
          <polygon
            points={`${padding.left},${padding.top + chartH} ${points.join(" ")} ${padding.left + chartW},${padding.top + chartH}`}
            fill={baseColor}
            opacity={0.1}
          />
        )}
        <polyline points={points.join(" ")} fill="none" stroke={baseColor} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      </>
    );
  };

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-3 max-w-xs">
      {title && (
        <div className="text-[10px] text-muted mb-1">{title}{unit && <span className="ml-1">({unit})</span>}</div>
      )}
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        {chart_type === "bar" ? renderBars() : renderLine()}
        {labels && labels.length > 0 && labels.map((label, i) => {
          const x = chart_type === "bar"
            ? padding.left + i * (chartW / values.length) + (chartW / values.length * 0.35)
            : padding.left + (i / (labels.length - 1)) * chartW;
          return (
            <text key={i} x={x} y={height - 4} textAnchor="middle" className="fill-muted" fontSize={8}>{label}</text>
          );
        })}
      </svg>
    </div>
  );
}
