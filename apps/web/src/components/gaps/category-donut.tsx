import type { GapCategory } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

export const CATEGORY_COLORS = ["#0F766E", "#2563EB", "#F59E0B", "#EA580C"];

export function CategoryDonut({
  categories,
  total,
}: {
  categories: GapCategory[];
  total: number;
}) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;

  const segments = categories.map((c, i) => ({
    name: c.name,
    color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    dash: c.percent * circumference,
    offset: categories
      .slice(0, i)
      .reduce((sum, prev) => sum + prev.percent * circumference, 0),
  }));

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-28 w-28 flex-shrink-0">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="#e5eeff"
            strokeWidth="14"
          />
          {segments.map((s) => (
            <circle
              key={s.name}
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={s.color}
              strokeWidth="14"
              strokeDasharray={`${s.dash} ${circumference}`}
              strokeDashoffset={-s.offset}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="font-label-mono text-[16px] font-bold leading-none text-on-surface">
            {formatNumber(total)}
          </span>
          <span className="mt-0.5 text-[10px] uppercase text-on-surface-variant">
            requests
          </span>
        </div>
      </div>

      <div className="flex w-full flex-col gap-1.5 text-caption">
        {categories.map((c, i) => (
          <div key={c.name} className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-on-surface">
              <span
                className={cn("h-2.5 w-2.5 rounded-full")}
                style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
              />
              {c.name}
            </span>
            <span className="font-label-mono font-medium text-on-surface">
              {Math.round(c.percent * 100)}%{" "}
              <span className="text-on-surface-variant">({c.count})</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
