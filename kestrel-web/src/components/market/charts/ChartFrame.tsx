import type { ReactNode } from "react";

/** Reusable chart frame: a left Y-axis value column + a plot area with dashed
 *  horizontal gridlines, a solid zero/baseline, and an optional X-axis label row
 *  aligned under the plot. Callers render their bars/line as `children` (absolutely
 *  positioned inside the plot) computing heights against the SAME `yMax` they pass.
 *
 *  Two modes:
 *  - symmetric (default): zero in the middle, axis labels +max / +½ / 0 / -½ / -max,
 *    for up/down net charts (institutional flow, net buy/sell, advance-decline).
 *  - non-symmetric: pass `yMin`; labels are max (top) / mid / min (bottom), for line
 *    charts (margin balance, price).
 *
 *  This is the shared frame behind every market net-bar / line chart so they all get
 *  consistent gridlines, axis values, and spacing instead of re-implementing them. */
export function ChartFrame({
  height = 140,
  fill = false,
  yMax,
  yMin,
  unit,
  fmt = (v) => v.toFixed(0),
  dates,
  xLabels = "none",
  axisWidth = 40,
  children,
}: {
  height?: number;
  /** Grow the plot to fill the parent's height instead of using a fixed `height`.
   *  The parent must be a flex column with a real height (the card stretches in a
   *  grid row) and this frame should sit in a `flex-1 min-h-0` slot. */
  fill?: boolean;
  yMax: number;
  /** Provide for a non-symmetric scale (e.g. a line chart). Omit for symmetric ±max. */
  yMin?: number;
  unit?: string;
  fmt?: (v: number) => string;
  dates?: string[];
  /** X-axis labels under the plot: weekday (Mon…), month-day (06-24), or just the
   *  first & last date (endpoints). */
  xLabels?: "none" | "weekday" | "monthday" | "endpoints";
  axisWidth?: number;
  children: ReactNode;
}) {
  const symmetric = yMin === undefined;
  const half = yMax / 2;

  // Axis label rows top→bottom and the gridline % positions they sit on.
  const ticks = symmetric
    ? [
        { pct: 0, label: `+${fmt(yMax)}`, strong: false },
        { pct: 25, label: `+${fmt(half)}`, strong: false },
        { pct: 50, label: "0", strong: true },
        { pct: 75, label: `-${fmt(half)}`, strong: false },
        { pct: 100, label: `-${fmt(yMax)}`, strong: false },
      ]
    : [
        { pct: 0, label: fmt(yMax), strong: false },
        { pct: 50, label: fmt((yMax + (yMin ?? 0)) / 2), strong: false },
        { pct: 100, label: fmt(yMin ?? 0), strong: false },
      ];

  // In fill mode the plot grows with the parent (no fixed px height).
  const sizeStyle = fill ? undefined : { height };

  return (
    <div className={fill ? "flex flex-col flex-1 min-h-0" : undefined}>
      <div className={`flex gap-2 ${fill ? "flex-1 min-h-0" : ""}`}>
        {/* Y-axis value labels */}
        <div className={`relative shrink-0 text-right ${fill ? "h-full" : ""}`} style={fill ? { width: axisWidth } : { width: axisWidth, height }}>
          {ticks.map((tk) => (
            <span
              key={tk.pct}
              className={`absolute right-0 text-[8px] font-mono ${tk.strong ? "text-muted/70" : "text-muted/45"}`}
              style={{
                top: `${tk.pct}%`,
                transform: tk.pct === 0 ? "translateY(0)" : tk.pct === 100 ? "translateY(-100%)" : "translateY(-50%)",
              }}
            >
              {tk.label}
            </span>
          ))}
          {unit && (
            <span className="absolute right-0 -top-3.5 text-[8px] font-mono text-muted/40">{unit}</span>
          )}
        </div>

        {/* Plot area: gridlines + baseline behind the caller's content */}
        <div className={`relative flex-1 min-w-0 ${fill ? "h-full" : ""}`} style={sizeStyle}>
          {ticks.map((tk) => (
            <div
              key={tk.pct}
              className={`absolute left-0 right-0 ${tk.strong ? "border-t border-border/60" : "border-t border-dashed border-border/25"}`}
              style={{ top: `${tk.pct}%` }}
            />
          ))}
          {children}
        </div>
      </div>

      {/* X-axis labels aligned under the plot (offset by the axis column width) */}
      {dates && dates.length > 0 && xLabels !== "none" && (
        <div className="flex mt-1" style={{ paddingLeft: axisWidth + 8 }}>
          {xLabels === "endpoints" ? (
            <div className="flex-1 flex justify-between text-[8px] font-mono text-muted/50">
              <span>{fmtDate(dates[0], "monthday")}</span>
              <span>{fmtDate(dates[dates.length - 1], "monthday")}</span>
            </div>
          ) : (
            <div className="flex-1 flex gap-0.5">
              {dates.map((d, i) => (
                <span key={`${d}-${i}`} className="flex-1 text-center text-[8px] font-mono text-muted/50 truncate">
                  {fmtDate(d, xLabels)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function fmtDate(date: string, mode: "weekday" | "monthday"): string {
  if (mode === "monthday") return date.slice(5);
  const d = new Date(date);
  return Number.isNaN(d.getTime()) ? "" : WEEKDAYS[d.getDay()];
}
