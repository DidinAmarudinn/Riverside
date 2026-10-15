import type { GapItem } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Sparkline } from "./sparkline";

function maxRequests(items: GapItem[]): number {
  return Math.max(1, ...items.map((i) => i.requests));
}

export function GapsTable({ items }: { items: GapItem[] }) {
  const max = maxRequests(items);

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-left">
        <thead>
          <tr className="h-10 bg-surface-container-low text-table-header text-on-surface-variant">
            <th className="w-[50px] px-4 py-2 text-[13px] font-medium">#</th>
            <th className="min-w-[190px] px-4 py-2 text-[13px] font-medium">
              Requested Product
            </th>
            <th className="min-w-[130px] px-4 py-2 text-[13px] font-medium">
              Category
            </th>
            <th className="min-w-[150px] px-4 py-2 text-right text-[13px] font-medium">
              Demand Volume
            </th>
            <th className="min-w-[100px] px-4 py-2 text-center text-[13px] font-medium">
              14d Trend
            </th>
            <th className="min-w-[220px] px-4 py-2 text-[13px] font-medium">
              Shopper Verbatim
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-container-low">
          {items.map((item) => (
            <tr
              key={item.rank}
              className="group transition-colors hover:bg-surface-container-low/50"
            >
              <td className="px-4 py-3 font-label-mono text-on-surface-variant">
                {String(item.rank).padStart(2, "0")}
              </td>
              <td className="px-4 py-3">
                <div className="text-body-medium font-semibold text-on-surface transition-colors group-hover:text-primary-container">
                  {item.name}
                </div>
                {item.subtitle ? (
                  <div className="text-caption text-on-surface-variant">
                    {item.subtitle}
                  </div>
                ) : null}
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center rounded-full bg-primary-fixed px-2 py-0.5 font-label-mono text-[12px] text-on-primary-fixed-variant">
                  {item.category}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <div className="font-label-mono font-bold text-on-surface">
                  {formatNumber(item.requests)}{" "}
                  <span className="text-caption font-normal text-on-surface-variant">
                    req
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-container">
                  <div
                    className="h-1.5 rounded-full bg-primary-container"
                    style={{ width: `${(item.requests / max) * 100}%` }}
                  />
                </div>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-col items-center">
                  <Sparkline
                    data={item.spark}
                    className={
                      item.trendDirection === "up"
                        ? "text-primary-container"
                        : "text-on-surface-variant"
                    }
                  />
                  <span
                    className={cn(
                      "text-[11px] font-label-mono font-medium",
                      item.trendDirection === "up"
                        ? "text-primary"
                        : "text-on-surface-variant",
                    )}
                  >
                    {item.trend7d}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3">
                <div
                  className="max-w-xs truncate text-caption italic text-on-surface"
                  title={item.quote}
                >
                  “{item.quote}”
                </div>
                <span className="mt-0.5 inline-block rounded bg-secondary-fixed px-1.5 py-0.5 font-label-mono text-[10px] text-on-secondary-fixed-variant">
                  Not carried
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
