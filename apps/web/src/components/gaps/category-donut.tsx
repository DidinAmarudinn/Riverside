"use client";

import { useState } from "react";
import type { GapCategory } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

// Ink and lime first, then greens and greys, so the biggest categories get the strongest colours.
export const CATEGORY_COLORS = ["#0E2A20", "#B7E36A", "#1F8A5B", "#5E7A6C", "#9AA39E", "#2E6B52", "#D9F0AD", "#C9D3CD", "#7FB98F", "#E4E7E5"];

/**
 * Ring of request share per category, every category the API returns; each slice ends in a rounded edge
 * that laps onto the next one.
 * Hovering (or tapping) a slice or its legend row puts that category in the centre.
 */
export function CategoryDonut({ categories, total }: { categories: GapCategory[]; total: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const sum = categories.reduce((s, c) => s + c.count, 0) || 1;
  const cx = 100;
  const cy = 100;
  const R = 74;
  const SW = 18;
  const H = SW / 2;
  const pt = (r: number, a: number) => `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
  // Every slice has the same shape: its end is a round cap that laps onto the next slice, its start is a
  // matching hollow that takes the previous slice's cap. The ring closes the same way, so no slice differs.
  const slice = (a0: number, a1: number, h: number) => {
    const ro = R + h;
    const ri = R - h;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    return [
      `M${pt(ro, a0)}`,
      `A${ro},${ro} 0 ${large} 1 ${pt(ro, a1)}`,
      `A${h},${h} 0 0 1 ${pt(ri, a1)}`,
      `A${ri},${ri} 0 ${large} 0 ${pt(ri, a0)}`,
      `A${h},${h} 0 0 0 ${pt(ro, a0)}`,
      "Z",
    ].join(" ");
  };
  // Tiny categories get a minimum visible angle (taken from the big ones) so a 1% slice still shows.
  const MIN = H / R + 0.09;
  const raw = categories.map((c) => (c.count / sum) * Math.PI * 2);
  const small = raw.reduce((s, r) => s + (r < MIN ? MIN : 0), 0);
  const bigTotal = raw.reduce((s, r) => s + (r < MIN ? 0 : r), 0) || 1;
  const spans = raw.map((r) => (r < MIN ? MIN : (r * (Math.PI * 2 - small)) / bigTotal));
  const bounds = spans.map((span, i) => {
    const a0 = -Math.PI / 2 + spans.slice(0, i).reduce((s, x) => s + x, 0);
    return [a0, a0 + span] as const;
  });
  const active = hover == null ? null : categories[hover];
  const color = (i: number) => CATEGORY_COLORS[i % CATEGORY_COLORS.length];

  return (
    <div className="flex flex-col items-center gap-4" onPointerLeave={() => setHover(null)}>
      <svg viewBox="-6 -6 212 212" className="h-auto w-48 flex-shrink-0" role="img" aria-label="Requests by category">
        {/* the hovered slice is drawn last and thicker, so it sits on top of its neighbours */}
        {[...categories.keys()]
          .sort((a, b) => (a === hover ? 1 : b === hover ? -1 : 0))
          .map((i) => (
            <path
              key={categories[i].name}
              d={slice(bounds[i][0], bounds[i][1], hover === i ? H + 3 : H)}
              fill={color(i)}
              stroke="#FFFFFF"
              strokeWidth="2"
              strokeLinejoin="round"
              className="cursor-pointer"
              onPointerEnter={() => setHover(i)}
              onPointerDown={() => setHover(i)}
            />
          ))}
        <text x={cx} y={cy + 6} textAnchor="middle" fontSize="30" fontWeight="500" fill="var(--color-on-surface)">
          {formatNumber(active ? active.count : total)}
        </text>
        <text x={cx} y={cy + 26} textAnchor="middle" fontSize="12" fill="var(--color-on-surface-variant)">
          {active ? `${Math.round(active.percent * 100)}% of requests` : "requests"}
        </text>
      </svg>

      <div className="flex w-full flex-col gap-0.5 text-caption">
        {categories.map((c, i) => (
          <div
            key={c.name}
            className={cn("flex cursor-default items-center justify-between gap-2 rounded-md px-2 py-1", hover === i && "bg-surface-container-low")}
            onPointerEnter={() => setHover(i)}
          >
            <span className="flex min-w-0 items-center gap-1.5 text-on-surface">
              <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ backgroundColor: color(i) }} />
              <span className="truncate">{c.name}</span>
            </span>
            <span className="flex-shrink-0 font-medium tabular-nums text-on-surface">
              {Math.round(c.percent * 100)}% <span className="text-on-surface-variant">({c.count})</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
