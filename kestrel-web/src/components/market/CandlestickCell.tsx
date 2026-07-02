interface CandlestickCellProps {
  open: number;
  high: number;
  low: number;
  close: number;
  width?: number;
  height?: number;
}

export function CandlestickCell({ open, high, low, close, width = 12, height = 32 }: CandlestickCellProps) {
  const range = high - low;
  if (range <= 0) return <div style={{ width, height }} />;

  const isUp = close >= open;
  const bodyTop = Math.max(open, close);
  const bodyBot = Math.min(open, close);

  const toY = (val: number) => ((high - val) / range) * (height - 4) + 2;

  const wickX = width / 2;
  const bodyWidth = Math.max(width * 0.6, 4);
  const bodyX = (width - bodyWidth) / 2;

  const wickTop = toY(high);
  const wickBot = toY(low);
  const bodyYTop = toY(bodyTop);
  const bodyYBot = toY(bodyBot);
  const bodyH = Math.max(bodyYBot - bodyYTop, 1);

  return (
    <svg width={width} height={height} className="shrink-0">
      {/* Upper wick */}
      <line
        x1={wickX} y1={wickTop}
        x2={wickX} y2={bodyYTop}
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1"
      />
      {/* Lower wick */}
      <line
        x1={wickX} y1={bodyYBot}
        x2={wickX} y2={wickBot}
        stroke={isUp ? "var(--up)" : "var(--down)"}
        strokeWidth="1"
      />
      {/* Body */}
      <rect
        x={bodyX}
        y={bodyYTop}
        width={bodyWidth}
        height={bodyH}
        fill={isUp ? "var(--up)" : "var(--down)"}
        opacity={isUp ? 1 : 0.85}
        rx="0.5"
      />
    </svg>
  );
}
