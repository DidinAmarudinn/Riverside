"use client";

import { useMemo, useState } from "react";
import { Info, Lightbulb, MessageSquareText } from "lucide-react";
import { useGaps } from "@/hooks/use-data";
import type { GapCategory, GapItem } from "@/lib/api/types";
import { Input } from "@/components/ui/input";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/common/states";
import { GapsTable } from "@/components/gaps/gaps-table";
import { CategoryDonut } from "@/components/gaps/category-donut";
import { formatNumber, formatRupiahCompact } from "@/lib/format";
import { cn } from "@/lib/utils";

export function GapsView() {
  const { data, isLoading, isError, refetch } = useGaps();
  const [category, setCategory] = useState<string>("All Categories");
  const [search, setSearch] = useState("");

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    data?.items.filter((i) => i.requests > 1).forEach((i) =>
      map.set(i.category, (map.get(i.category) ?? 0) + 1),
    );
    return map;
  }, [data]);

  // Names asked only once are mostly unmatched typos; they stay in the totals but not in the ranked list.
  const ranked = useMemo(
    () => (data?.items ?? []).filter((i) => i.requests > 1),
    [data],
  );
  const oneOffs = (data?.items.length ?? 0) - ranked.length;

  const filtered = useMemo(() => {
    let items = ranked;
    if (category !== "All Categories") {
      items = items.filter((i) => i.category === category);
    }
    if (search.trim()) {
      const needle = search.trim().toLowerCase();
      items = items.filter(
        (i) =>
          i.name.toLowerCase().includes(needle) ||
          i.quote.toLowerCase().includes(needle),
      );
    }
    return items;
  }, [ranked, category, search]);

  if (isLoading) return <CardSkeleton rows={8} />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Could not load assortment gaps"
        onRetry={() => refetch()}
      />
    );
  }

  const categories = ["All Categories", ...counts.keys()];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col justify-between gap-4 pt-2 md:flex-row md:items-end">
        <div>
          <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
            Assortment gaps
          </h1>
          <p className="mt-1 text-body-default text-on-surface-variant">
            Products shoppers asked the kiosk for that this store does not
            carry. Spelling variants are merged under one name.
          </p>
        </div>
      </div>

      <div className="flex flex-col justify-between gap-4 rounded-xl bg-surface-container-lowest p-4 lg:flex-row lg:items-center">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0">
          {categories.map((c) => {
            const active = category === c;
            const count = c === "All Categories" ? ranked.length : counts.get(c);
            return (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2 text-caption transition",
                  active
                    ? "bg-primary-fixed font-semibold text-on-primary-fixed"
                    : "bg-surface-container-low text-on-surface hover:bg-surface-container-high",
                )}
              >
                {c}
                {count ? (
                  <span
                    className={cn(
                      "rounded-full px-1.5 text-[11px]",
                      active
                        ? "bg-white/60 text-on-primary-fixed"
                        : "bg-surface-container text-on-surface-variant",
                    )}
                  >
                    {count}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        <div className="relative w-full flex-shrink-0 sm:w-64">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by product or quote…"
            aria-label="Filter gaps"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <div className="overflow-hidden rounded-xl bg-surface-container-lowest">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-2">
                <span className="text-headline-lg text-on-surface">
                  Most requested, not carried
                </span>
                <span className="rounded-full bg-surface-container-high px-2 py-0.5 font-label-mono text-caption text-on-surface">
                  {ranked.length} products
                </span>
              </div>
              <span className="flex items-center gap-1 text-caption text-on-surface-variant">
                <Info className="h-4 w-4 text-primary-container" aria-hidden />
                Sorted by requests
              </span>
            </div>
            {filtered.length === 0 ? (
              <EmptyState
                title="No matching products"
                description="Try another category or keyword."
              />
            ) : (
              <div className="px-6 pb-5">
                <GapsTable items={filtered} />
              </div>
            )}
            <div className="flex flex-col items-center justify-between gap-1 border-t border-outline-variant px-6 py-3 text-caption text-on-surface-variant sm:flex-row">
              <span className="flex items-center gap-1">
                <MessageSquareText className="h-4 w-4 text-primary-container" aria-hidden />
                Read by Gemini from informal Indonesian kiosk chats.
                {oneOffs > 0 ? ` ${oneOffs} names asked only once are not listed.` : ""}
              </span>
              <span className="font-label-mono">
                Showing {filtered.length} of {ranked.length}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-4">
          <div className="flex flex-col gap-4 rounded-xl bg-surface-container-lowest p-6">
            <div className="flex items-center justify-between">
              <span className="text-headline-sm text-on-surface">
                Potential opportunity
              </span>
              <span className="rounded bg-surface-container px-2 py-0.5 font-label-mono text-[11px] text-on-surface">
                90-day simulation
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-surface-container-low p-3">
                <span className="block text-caption text-on-surface-variant">
                  Unmet requests
                </span>
                <span className="mt-1 block text-kpi-stat-mobile tabular-nums text-on-surface">
                  {formatNumber(data.summary.totalRequests)}
                </span>
              </div>
              <div className="rounded-lg bg-surface-container-low p-3">
                <span className="block text-caption text-on-surface-variant">
                  Revenue at stake
                </span>
                <span className="mt-1 block text-kpi-stat-mobile tabular-nums text-on-surface">
                  {formatRupiahCompact(data.summary.lostRevenueExposureIdr)}
                </span>
                <span className="mt-0.5 block text-caption text-on-surface-variant">
                  Requests × typical category price
                </span>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between text-body-medium font-semibold text-on-surface">
                <span>Requests by category</span>
                <span className="text-caption text-on-surface-variant">
                  {data.summary.categories.length} categories
                </span>
              </div>
              <CategoryDonut
                categories={data.summary.categories}
                total={data.summary.totalRequests}
              />
            </div>

            <div className="rounded-lg bg-secondary-fixed p-4">
              <div className="mb-1 flex items-center gap-1 text-headline-sm text-[13px] text-primary-container">
                <Lightbulb className="h-4 w-4" aria-hidden />
                What stands out
              </div>
              <p className="text-body-default leading-relaxed text-on-surface-variant">
                {insight(ranked[0], data.summary.categories[0])}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** One sentence built from the data on screen, never canned copy. */
function insight(top: GapItem | undefined, category: GapCategory | undefined): string {
  if (!top) return "No product has been asked for more than once yet.";
  const lead = `${top.name} is the most requested product this store does not carry (${formatNumber(top.requests)} requests).`;
  if (!category) return lead;
  return `${lead} ${category.name} makes up ${Math.round(category.percent * 100)}% of all such requests.`;
}
