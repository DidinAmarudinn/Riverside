"use client";

import { useState } from "react";
import { formatDateWib, formatNumber } from "@/lib/format";

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

const fmtQty = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 1 });

/**
 * Track bars in the site's chart style: a grey track per day, an ink bar for units sold, one lime dot per
 * shopper who asked. With `forecast`, the next days follow on a light panel with forecast A (dashed grey)
 * and forecast B (green). Hovering (or tapping) a day shows its numbers.
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
  const [hover, setHover] = useState<number | null>(null);
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

  const hovered = hover == null ? null : hover < days.length ? { kind: "day" as const, d: days[hover] } : { kind: "fc" as const, f: forecast[hover - days.length] };
  const tipLeft = hover == null ? 0 : (tick(hover) / W) * 100;

  return (
    <div className="relative" onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full touch-pan-y" role="img" aria-label={label}>
        {days.map((d, i) => {
          const x = i * bw + (bw - w) / 2;
          return (
            <g key={d.date}>
              <rect
                x={x}
                y={top}
                width={w}
                height={base - top}
                rx={w / 2}
                fill={hover === i ? "var(--color-surface-container-highest)" : "var(--color-surface-container-high)"}
              />
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
            {hover != null && hover >= days.length ? (
              <line x1={tick(hover)} x2={tick(hover)} y1={top} y2={base} stroke="var(--color-outline-variant)" strokeWidth="2" />
            ) : null}
            <polyline points={line("a")} fill="none" stroke="var(--color-outline)" strokeWidth="3" strokeDasharray="5 6" strokeLinecap="round" strokeLinejoin="round" />
            <polyline points={line("b")} fill="none" stroke="var(--color-primary-container)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            {hovered?.kind === "fc" ? (
              <>
                {hovered.f.a != null ? <circle cx={tick(hover!)} cy={y(hovered.f.a)} r="5" fill="var(--color-outline)" /> : null}
                {hovered.f.b != null ? <circle cx={tick(hover!)} cy={y(hovered.f.b)} r="5" fill="var(--color-primary-container)" /> : null}
              </>
            ) : null}
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
        {/* hit areas, one per day, on top of everything */}
        {Array.from({ length: n }, (_, i) => (
          <rect
            key={i}
            x={i * bw}
            y={0}
            width={bw}
            height={base}
            fill="transparent"
            onPointerEnter={() => setHover(i)}
            onPointerDown={() => setHover(i)}
          />
        ))}
      </svg>

      {hovered ? (
        <div
          className="pointer-events-none absolute top-0 z-10 min-w-[150px] rounded-lg bg-primary px-3 py-2 text-caption text-white shadow-[0_8px_24px_rgba(14,42,32,0.25)]"
          style={{
            left: `${tipLeft}%`,
            transform: `translate(${tipLeft > 70 ? "-100%" : tipLeft < 30 ? "0" : "-50%"}, -8px)`,
          }}
          role="status"
        >
          {hovered.kind === "day" ? (
            <>
              <div className="font-semibold">{formatDateWib(hovered.d.date)}</div>
              <div>
                Sold (POS): <span className="font-semibold">{formatNumber(hovered.d.sold)}</span>
                {hovered.d.sold === 0 && hover! >= firstOut && firstOut >= 0 ? " · sold out" : ""}
              </div>
              {hovered.d.asked ? (
                <div>
                  <span className="mr-1 inline-block h-2 w-2 rounded-full bg-primary-fixed" />
                  Asked at the kiosk: <span className="font-semibold">{formatNumber(hovered.d.asked)}</span>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <div className="font-semibold">{formatDateWib(hovered.f.date)} · forecast</div>
              <div>A (POS only): <span className="font-semibold">{hovered.f.a != null ? fmtQty(hovered.f.a) : "—"}</span></div>
              <div className="text-primary-fixed">
                B (POS + unmet): <span className="font-semibold">{hovered.f.b != null ? fmtQty(hovered.f.b) : "—"}</span>
              </div>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
