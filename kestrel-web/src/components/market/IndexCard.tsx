interface Props {
  label: string;
  code: string;
  value: number | null;
  change?: number;
  changePct?: number;
  sparkData?: number[];
}

export function IndexCard({ label, code, value, change, changePct, sparkData }: Props) {
  const isUp = (changePct ?? 0) >= 0;

  return (
    <div className="card-atmospheric p-5 flex flex-col justify-between min-h-[140px]">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted">{label}</span>
        <span className="text-[10px] font-mono text-muted/60 uppercase tracking-wider">{code}</span>
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold font-mono text-foreground">
          {value?.toLocaleString() ?? "—"}
        </div>
        {changePct !== undefined && (
          <div className={`flex items-center gap-2 mt-1 ${isUp ? "text-up" : "text-down"}`}>
            <span className="text-xs font-mono font-semibold">
              {isUp ? "▲" : "▼"} {change !== undefined ? `${isUp ? "+" : ""}${change.toFixed(2)}` : ""}
            </span>
            <span className="text-xs font-mono">
              ({isUp ? "+" : ""}{changePct.toFixed(2)}%)
            </span>
          </div>
        )}
      </div>
      {/* Sparkline */}
      {sparkData && sparkData.length > 1 && (
        <div className="mt-3 h-8">
          <Sparkline data={sparkData} isUp={isUp} />
        </div>
      )}
    </div>
  );
}

function Sparkline({ data, isUp }: { data: number[]; isUp: boolean }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const h = 32;
  const w = 100;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`spark-grad-${isUp ? "up" : "down"}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={isUp ? "var(--up)" : "var(--down)"} stopOpacity="0.3" />
          <stop offset="100%" stopColor={isUp ? "var(--up)" : "var(--down)"} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${h} ${points} ${w},${h}`}
        fill={`url(#spark-grad-${isUp ? "up" : "down"})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
