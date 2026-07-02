import { ChartFrame } from "./ChartFrame";

export interface NetSeries {
  /** Bar fill — a Tailwind bg-* class (e.g. "bg-up", "bg-down", "bg-signal"). */
  color: string;
}

/** Grouped up/down net-bar chart over a set of dates, on the shared ChartFrame
 *  (gridlines + zero baseline + ±max axis labels + X labels). Each date carries
 *  one value per series; positive values draw above the zero line, negative below.
 *
 *  Replaces the hand-rolled net-bar plots in InstitutionalFlow / ChipDaily /
 *  AdvanceDeclineHistory / GovernmentBankTab so they share one clear look. */
export function NetBarsChart({
  dates,
  series,
  values,
  height = 140,
  fill = false,
  unit,
  fmt = (v) => v.toFixed(0),
  xLabels = "endpoints",
  barMaxWidth = 7,
  title,
}: {
  dates: string[];
  /** Series definitions (color per series). 1 series → simple net bars. */
  series: NetSeries[];
  /** values[dateIndex][seriesIndex] = net value (sign decides up/down). */
  values: number[][];
  height?: number;
  /** Grow to fill the parent's height (parent must be a flex column). */
  fill?: boolean;
  unit?: string;
  fmt?: (v: number) => string;
  xLabels?: "none" | "weekday" | "monthday" | "endpoints";
  barMaxWidth?: number;
  title?: string;
}) {
  if (dates.length === 0) return null;
  const yMax = Math.max(
    ...values.flat().map((v) => Math.abs(v)),
    1,
  );

  return (
    <div className={fill ? "flex flex-col flex-1 min-h-0" : undefined}>
      {title && <span className="text-[10px] text-muted/60 mb-1.5 block">{title}</span>}
      <ChartFrame height={height} fill={fill} yMax={yMax} unit={unit} fmt={fmt} dates={dates} xLabels={xLabels}>
        <div className="absolute inset-0 flex gap-0.5">
          {dates.map((date, di) => (
            <div key={`${date}-${di}`} className="flex-1 flex flex-col items-center min-w-0 h-full" title={tooltip(date, values[di], fmt, unit)}>
              {/* Upper half (positive) — bars grow down from the zero line */}
              <div className="flex items-end gap-px justify-center w-full h-1/2">
                {series.map((s, si) => {
                  const v = values[di]?.[si] ?? 0;
                  return (
                    <div
                      key={si}
                      className={`flex-1 rounded-t-sm ${v > 0 ? s.color : "bg-transparent"}`}
                      style={{ maxWidth: barMaxWidth, height: v > 0 ? `${Math.max((Math.abs(v) / yMax) * 100, 3)}%` : "0%" }}
                    />
                  );
                })}
              </div>
              {/* Lower half (negative) */}
              <div className="flex items-start gap-px justify-center w-full h-1/2">
                {series.map((s, si) => {
                  const v = values[di]?.[si] ?? 0;
                  return (
                    <div
                      key={si}
                      className={`flex-1 rounded-b-sm ${v < 0 ? s.color : "bg-transparent"}`}
                      style={{ maxWidth: barMaxWidth, height: v < 0 ? `${Math.max((Math.abs(v) / yMax) * 100, 3)}%` : "0%", opacity: 0.8 }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </ChartFrame>
    </div>
  );
}

function tooltip(date: string, vals: number[] | undefined, fmt: (v: number) => string, unit?: string): string {
  if (!vals) return date;
  const parts = vals.map((v) => `${v >= 0 ? "+" : ""}${fmt(v)}`).join(" / ");
  return `${date.slice(5)}: ${parts}${unit ? " " + unit : ""}`;
}
