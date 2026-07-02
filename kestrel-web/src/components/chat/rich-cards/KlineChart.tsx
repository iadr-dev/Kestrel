interface Overlay {
  name: string;
  values: number[];
}

interface Props {
  data: {
    stock_id: string;
    stock_name?: string;
    dates: string[];
    open: number[];
    high: number[];
    low: number[];
    close: number[];
    volume?: number[];
    overlays?: Overlay[];
  };
}

const OVERLAY_COLORS = ["#f5a623", "#4a90d9", "#9b59b6", "#16a085"];

export function KlineChart({ data }: Props) {
  const { stock_id, stock_name, dates, open, high, low, close, volume, overlays } = data;
  if (!high?.length || !low?.length || !close?.length) return null;

  const n = close.length;
  const width = 340;
  const priceH = 140;
  const volH = volume?.length ? 32 : 0;
  const pad = { top: 8, right: 8, bottom: 16, left: 8 };
  const chartW = width - pad.left - pad.right;

  // Price scale spans candle highs/lows + any overlay values.
  const overlayVals = (overlays || []).flatMap((o) => o.values.filter((v) => v != null));
  const hi = Math.max(...high, ...overlayVals);
  const lo = Math.min(...low, ...overlayVals);
  const range = hi - lo || 1;
  const yPrice = (v: number) => pad.top + (1 - (v - lo) / range) * priceH;
  const xAt = (i: number) => pad.left + (n === 1 ? chartW / 2 : (i / (n - 1)) * chartW);
  const slot = chartW / n;
  const bodyW = Math.max(slot * 0.6, 2);

  const up = close[n - 1] >= (open[0] ?? close[0]);
  const maxVol = volume?.length ? Math.max(...volume) || 1 : 1;

  return (
    <div className="my-3 border border-border/60 rounded-2xl overflow-hidden bg-surface p-3 max-w-md">
      <div className="flex items-baseline justify-between mb-1">
        <div className="text-sm font-semibold">
          {stock_name || stock_id} <span className="text-[10px] text-muted font-mono">{stock_id}</span>
        </div>
        <div className={`text-sm font-mono font-semibold ${up ? "text-up" : "text-down"}`}>
          {close[n - 1]?.toLocaleString()}
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${priceH + volH + pad.top + pad.bottom}`} className="w-full h-auto">
        {/* Candlesticks */}
        {close.map((c, i) => {
          const o = open[i] ?? c;
          const x = xAt(i);
          const isUp = c >= o;
          const color = isUp ? "var(--up)" : "var(--down)";
          const bodyTop = yPrice(Math.max(o, c));
          const bodyBot = yPrice(Math.min(o, c));
          return (
            <g key={i}>
              <line x1={x} y1={yPrice(high[i])} x2={x} y2={yPrice(low[i])} stroke={color} strokeWidth={1} />
              <rect
                x={x - bodyW / 2}
                y={bodyTop}
                width={bodyW}
                height={Math.max(bodyBot - bodyTop, 1)}
                fill={color}
                opacity={isUp ? 0.9 : 1}
              />
            </g>
          );
        })}

        {/* MA / indicator overlays */}
        {(overlays || []).map((ov, oi) => {
          const pts = ov.values
            .map((v, i) => (v == null ? null : `${xAt(i)},${yPrice(v)}`))
            .filter(Boolean)
            .join(" ");
          if (!pts) return null;
          return <polyline key={oi} points={pts} fill="none" stroke={OVERLAY_COLORS[oi % OVERLAY_COLORS.length]} strokeWidth={1.2} strokeLinejoin="round" />;
        })}

        {/* Volume bars */}
        {volume?.length === n && volume.map((v, i) => {
          const h = (v / maxVol) * (volH - 4);
          const isUp = close[i] >= (open[i] ?? close[i]);
          return (
            <rect
              key={`v${i}`}
              x={xAt(i) - bodyW / 2}
              y={pad.top + priceH + (volH - h)}
              width={bodyW}
              height={h}
              fill={isUp ? "var(--up)" : "var(--down)"}
              opacity={0.4}
            />
          );
        })}
      </svg>

      <div className="flex items-center justify-between text-[9px] text-muted mt-1">
        <span>{dates?.[0]}</span>
        {overlays?.length ? (
          <span className="flex gap-2">
            {overlays.map((o, i) => (
              <span key={i} style={{ color: OVERLAY_COLORS[i % OVERLAY_COLORS.length] }}>{o.name}</span>
            ))}
          </span>
        ) : null}
        <span>{dates?.[dates.length - 1]}</span>
      </div>
    </div>
  );
}
