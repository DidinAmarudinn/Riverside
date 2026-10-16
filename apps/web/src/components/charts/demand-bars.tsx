import { formatDateWib } from "@/lib/format";

export interface DemandDay {
  date: string;
  sold: number;
  /** Shoppers who asked at the kiosk while it was out of stock. */
  asked: number;
}

export interface ForecastDay {
  date: string;
  a: number | null;
  b: number | null;
}

/**
 * Track bars in the site's chart style: a grey track per day, an ink bar for units sold, one lime dot per
 * shopper who asked. With `forecast`, the next days follow on a light panel with forecast A (dashed grey)
 * and forecast B (green).
 */
export function DemandBars({
  days,
  forecast = [],
  label,
  height = 210,
}: {
  days: DemandDay[];
  forecast?: ForecastDay[];
  label: string;
  height?: number;
}) {
  if (!days.length) return null;
  const W = 680;
  const H = height;
  const base = H - 28;
  const top = 12;
  const n = days.length + forecast.length;
  const bw = W / n;
  const w = bw * 0.64;
  const max = Math.max(8, ...days.map((d) => d.sold), ...forecast.map((f) => Math.max(f.a ?? 0, f.b ?? 0))) * 1.05;
  const y = (v: number) => base - (v / max) * (base - top);
  const firstOut = days.findIndex((d, i) => d.sold === 0 && days.slice(i).every((x) => x.sold === 0));
  const x0 = days.length * bw;
  const line = (key: "a" | "b") =>
    forecast
      .map((f, i) => (f[key] == null ? null : `${x0 + i * bw + bw / 2},${y(f[key] as number)}`))
      .filter(Boolean)
      .join(" ");
  const tick = (i: number) => i * bw + bw / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={label}>
      {days.map((d, i) => {
        const x = i * bw + (bw - w) / 2;
        return (
          <g key={d.date}>
            <rect x={x} y={top} width={w} height={base - top} rx={w / 2} fill="var(--color-surface-container-high)" />
            {d.sold > 0 ? (
              <rect x={x} y={y(d.sold)} width={w} height={base - y(d.sold)} rx={w / 2} fill="var(--color-primary)" />
            ) : null}
            {Array.from({ length: d.asked }, (_, k) => (
              <circle
                key={k}
                cx={x + w / 2}
                cy={base - w / 2 - 2 - k * (w + 3)}
                r={w / 2 - 0.5}
                fill="var(--color-primary-fixed)"
                stroke={d.sold > 0 ? "var(--color-primary)" : "none"}
                strokeWidth="1.2"
              />
            ))}
          </g>
        );
      })}
      {forecast.length ? (
        <g>
          <rect x={x0} y={top} width={W - x0} height={base - top} rx="12" fill="var(--color-surface-container-low)" />
          <polyline points={line("a")} fill="none" stroke="var(--color-outline)" strokeWidth="3" strokeDasharray="5 6" strokeLinecap="round" strokeLinejoin="round" />
          <polyline points={line("b")} fill="none" stroke="var(--color-primary-container)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          <text x={x0 + 8} y={top + 16} fill="var(--color-on-surface-variant)" fontSize="13">
            next {forecast.length} days
          </text>
        </g>
      ) : null}
      <text x="0" y={H - 6} fill="var(--color-on-surface-variant)" fontSize="13">
        {formatDateWib(days[0].date)}
      </text>
      {firstOut > 2 && firstOut < days.length - 3 ? (
        <text x={tick(firstOut)} y={H - 6} fill="var(--color-on-surface-variant)" fontSize="13" textAnchor="middle">
          {formatDateWib(days[firstOut].date)}
        </text>
      ) : null}
      <text
        x={forecast.length ? tick(days.length - 1) : W}
        y={H - 6}
        fill="var(--color-on-surface-variant)"
        fontSize="13"
        textAnchor={forecast.length ? "middle" : "end"}
      >
        {formatDateWib(days[days.length - 1].date)}
      </text>
      {forecast.length ? (
        <text x={W} y={H - 6} fill="var(--color-on-surface-variant)" fontSize="13" textAnchor="end">
          {formatDateWib(forecast[forecast.length - 1].date)}
        </text>
      ) : null}
    </svg>
  );
}
