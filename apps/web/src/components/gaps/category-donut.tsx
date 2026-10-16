"use client";

import { useState } from "react";
import type { GapCategory } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export const CATEGORY_COLORS = ["#0E2A20", "#B7E36A", "#1F8A5B", "#9AA39E", "#C9D3CD", "#5E7A6C"];

/** Ring of request share per category; hovering a slice or its legend row shows that category in the centre. */
export function CategoryDonut({ categories, total }: { categories: GapCategory[]; total: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const segments = categories.map((c, i) => ({
    name: c.name,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    dash: c.percent * circumference,
    offset: categories.slice(0, i).reduce((sum, prev) => sum + prev.percent * circumference, 0),
  }));
  const active = hover == null ? null : categories[hover];

  return (
    <div className="flex items-center gap-4" onPointerLeave={() => setHover(null)}>
      <div className="relative h-32 w-32 flex-shrink-0">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" role="img" aria-label="Requests by category">
          <circle cx="50" cy="50" r={radius} fill="none" stroke="#E4E7E5" strokeWidth="14" />
          {segments.map((s, i) => (
            <circle
              key={s.name}
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={s.color}
              strokeWidth={hover === i ? 18 : 14}
              strokeDasharray={`${s.dash} ${circumference}`}
              strokeDashoffset={-s.offset}
              opacity={hover == null || hover === i ? 1 : 0.35}
              className="cursor-pointer transition-[stroke-width,opacity]"
              onPointerEnter={() => setHover(i)}
              onPointerDown={() => setHover(i)}
            />
          ))}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-5 text-center">
          <span className="text-[18px] font-semibold leading-none tabular-nums text-on-surface">
            {formatNumber(active ? active.count : total)}
          </span>
          <span className="mt-1 text-[10px] leading-tight text-on-surface-variant">
            {active ? `${active.name} · ${Math.round(active.percent * 100)}%` : "requests"}
          </span>
        </div>
      </div>

      <div className="flex w-full flex-col gap-1 text-caption">
        {categories.map((c, i) => (
          <div
            key={c.name}
            className={cn("flex cursor-default items-center justify-between rounded-md px-1.5 py-0.5", hover === i && "bg-surface-container-low")}
            onPointerEnter={() => setHover(i)}
          >
            <span className="flex items-center gap-1.5 text-on-surface">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }} />
              {c.name}
            </span>
            <span className="font-medium tabular-nums text-on-surface">
              {Math.round(c.percent * 100)}% <span className="text-on-surface-variant">({c.count})</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
