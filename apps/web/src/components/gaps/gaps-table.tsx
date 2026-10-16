"use client";

import { useState } from "react";
import type { GapItem } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Ranked list of products shoppers asked for and the store does not carry: track bar per product, top one in lime. Hover a row for its details. */
export function GapsTable({ items }: { items: GapItem[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...items.map((i) => i.requests));
  const total = items.reduce((s, i) => s + i.requests, 0) || 1;
  return (
    <ol className="flex flex-col gap-1" onPointerLeave={() => setHover(null)}>
      {items.map((item, i) => (
        <li
          key={item.name}
          className={cn(
            "relative grid grid-cols-[minmax(0,1.3fr)_minmax(0,2fr)_auto] items-center gap-3 rounded-lg px-2 py-1.5 sm:gap-4",
            hover === i && "bg-surface-container-low",
          )}
          onPointerEnter={() => setHover(i)}
          onPointerDown={() => setHover(i)}
        >
          <div className="min-w-0">
            <span className="block truncate text-body-medium text-on-surface">{item.name}</span>
            <span className="block truncate text-caption italic text-on-surface-variant">“{item.quote}”</span>
          </div>
          <div className="relative">
            <div className="h-2.5 overflow-hidden rounded-full bg-surface-container-high" aria-hidden>
              <div
                className={cn("h-full rounded-full", i === 0 ? "bg-primary-fixed" : "bg-primary")}
                style={{ width: `${(item.requests / max) * 100}%` }}
              />
            </div>
            {hover === i ? (
              <div
                className="pointer-events-none absolute bottom-4 z-10 w-max max-w-[240px] -translate-x-1/2 rounded-lg bg-primary px-3 py-2 text-caption text-white shadow-[0_8px_24px_rgba(14,42,32,0.25)]"
                style={{ left: `${Math.min(85, Math.max(15, (item.requests / max) * 100))}%` }}
                role="status"
              >
                <div className="font-semibold">{item.name}</div>
                <div>
                  {formatNumber(item.requests)} requests · {Math.round((item.requests / total) * 100)}% of the list
                </div>
                <div>{item.category} · last 7 days {item.trend7d}</div>
              </div>
            ) : null}
          </div>
          <span className="w-14 text-right">
            <span className="block text-headline-md tabular-nums text-on-surface">{formatNumber(item.requests)}</span>
            <span className="block text-[11px] text-on-surface-variant">{item.trend7d} 7d</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
