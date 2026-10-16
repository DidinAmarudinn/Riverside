import type { GapItem } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Ranked list of products shoppers asked for and the store does not carry: track bar per product, top one in lime. */
export function GapsTable({ items }: { items: GapItem[] }) {
  const max = Math.max(1, ...items.map((i) => i.requests));
  return (
    <ol className="flex flex-col gap-3">
      {items.map((item, i) => (
        <li key={item.name} className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,2fr)_auto] items-center gap-3 sm:gap-4">
          <div className="min-w-0">
            <span className="block truncate text-body-medium text-on-surface">{item.name}</span>
            <span className="block truncate text-caption italic text-on-surface-variant">“{item.quote}”</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface-container-high" aria-hidden>
            <div
              className={cn("h-full rounded-full", i === 0 ? "bg-primary-fixed" : "bg-primary")}
              style={{ width: `${(item.requests / max) * 100}%` }}
            />
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
