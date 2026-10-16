"use client";

import { useMemo, useState } from "react";
import { Lightbulb, MessageSquareText } from "lucide-react";
import { useGaps } from "@/hooks/use-data";
import type { GapCategory, GapItem } from "@/lib/api/types";
import { EmptyState, ErrorState } from "@/components/common/states";
import { GapsTable } from "@/components/gaps/gaps-table";
import { CategoryDonut } from "@/components/gaps/category-donut";
import { formatNumber, formatRupiahCompact } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ScrollRow } from "@/components/ui/scroll-row";

const ALL = "All";

/**
 * The page frame renders at once; only the parts that wait for the API (chips, the list, the donut and the
 * two totals) show a placeholder, the way the home page does.
 */
export function GapsView() {
  const { data, isLoading, isError, refetch } = useGaps();
  const [category, setCategory] = useState<string>(ALL);
  const [search, setSearch] = useState("");

  // Names asked only once are mostly unmatched typos; they stay in the totals but not in the ranked list.
  const ranked = useMemo(() => (data?.items ?? []).filter((i) => i.requests > 1), [data]);
  const oneOffs = (data?.items.length ?? 0) - ranked.length;
  const categories = useMemo(() => [ALL, ...new Set(ranked.map((i) => i.category))], [ranked]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return ranked.filter(
      (i) =>
        (category === ALL || i.category === category) &&
        (!needle || i.name.toLowerCase().includes(needle) || i.quote.toLowerCase().includes(needle)),
    );
  }, [ranked, category, search]);

  const loading = isLoading || (!data && !isError);

  return (
    <div className="flex flex-col gap-4">
      <div className="pt-2">
        <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
          Assortment gaps
        </h1>
        <p className="mt-1 text-body-default text-on-surface-variant">
          Products shoppers asked the kiosk for that this store does not carry. Spelling variants are merged under
          one name.
        </p>
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <section className="flex min-w-0 flex-col gap-4 rounded-xl bg-surface-container-lowest p-6 lg:col-span-8">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-headline-lg text-on-surface">Most requested, not carried</h2>
            <span className="text-caption text-on-surface-variant">
              {loading ? "90-day simulation" : `90-day simulation · ${filtered.length} of ${ranked.length} products`}
            </span>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <ScrollRow className="flex-1">
              {loading
                ? [64, 120, 84, 96].map((w) => (
                    <span key={w} className="h-[33px] flex-shrink-0 animate-pulse rounded-full bg-surface-container-low" style={{ width: w }} />
                  ))
                : categories.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCategory(c)}
                      aria-pressed={category === c}
                      className={cn(
                        "flex-shrink-0 whitespace-nowrap rounded-full px-3.5 py-[7px] text-[13px] text-on-surface transition-colors",
                        category === c ? "bg-primary-fixed font-semibold" : "bg-surface-container-low hover:bg-surface-container-high",
                      )}
                    >
                      {c}
                    </button>
                  ))}
            </ScrollRow>
            <label htmlFor="gap-search" className="sr-only">
              Filter gaps
            </label>
            <input
              id="gap-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by product or quote…"
              autoComplete="off"
              className="w-full flex-shrink-0 rounded-full bg-surface-container-low px-4 py-2 text-body-default text-on-surface placeholder:text-on-surface-variant focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-container sm:w-56"
            />
          </div>

          {isError ? (
            <ErrorState title="Could not load assortment gaps" onRetry={() => refetch()} />
          ) : loading ? (
            <div className="flex flex-col gap-3" aria-hidden>
              {Array.from({ length: 8 }, (_, i) => (
                <div key={i} className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,2fr)_auto] items-center gap-4 px-2 py-1.5">
                  <span className="h-9 animate-pulse rounded-lg bg-surface-container-low" />
                  <span className="h-2.5 animate-pulse rounded-full bg-surface-container-low" style={{ width: `${90 - i * 9}%` }} />
                  <span className="h-6 w-10 animate-pulse rounded-md bg-surface-container-low" />
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState title="No matching products" description="Try another category or keyword." />
          ) : (
            <GapsTable items={filtered} />
          )}

          <p className="flex items-center gap-1.5 border-t border-outline-variant pt-3 text-caption text-on-surface-variant">
            <MessageSquareText className="h-4 w-4 flex-shrink-0 text-primary-container" aria-hidden />
            Read by the signal extractor from informal Indonesian kiosk chats.
            {oneOffs > 0 ? ` ${oneOffs} names asked only once are not listed.` : ""}
          </p>
        </section>

        <div className="flex flex-col gap-4 lg:col-span-4">
          <section className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="text-headline-md text-on-surface">Requests by category</h2>
              {data ? (
                <span className="text-caption text-on-surface-variant">{data.summary.categories.length} categories</span>
              ) : null}
            </div>
            {data ? (
              <CategoryDonut categories={data.summary.categories} total={data.summary.totalRequests} />
            ) : (
              <div className="flex flex-col items-center gap-3" aria-hidden>
                <span className="my-4 h-[150px] w-[150px] animate-pulse rounded-full border-[24px] border-surface-container-low" />
                <span className="h-4 w-full animate-pulse rounded bg-surface-container-low" />
              </div>
            )}
          </section>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1 rounded-xl bg-surface-container-lowest p-5">
              <span className="text-caption text-on-surface-variant">Requests</span>
              {data ? (
                <span className="text-kpi-stat tabular-nums text-on-surface">{formatNumber(data.summary.totalRequests)}</span>
              ) : (
                <span className="h-10 w-20 animate-pulse rounded-md bg-surface-container-low" />
              )}
            </div>
            <div className="flex flex-col gap-1 rounded-xl bg-surface-container-lowest p-5">
              <span className="text-caption text-on-surface-variant">Revenue at stake</span>
              {data ? (
                <span className="text-kpi-stat tabular-nums text-on-surface">
                  {formatRupiahCompact(data.summary.lostRevenueExposureIdr)}
                </span>
              ) : (
                <span className="h-10 w-24 animate-pulse rounded-md bg-surface-container-low" />
              )}
              <span className="text-[11px] text-on-surface-variant">requests × typical category price</span>
            </div>
          </div>

          {data ? (
            <div className="rounded-xl bg-secondary-fixed p-5">
              <div className="mb-1 flex items-center gap-1.5 text-body-medium font-semibold text-on-surface">
                <Lightbulb className="h-4 w-4" aria-hidden />
                What stands out
              </div>
              <p className="text-body-default leading-relaxed text-on-surface">
                {insight(ranked[0], [...data.summary.categories].sort((a, b) => b.count - a.count)[0])}
              </p>
            </div>
          ) : null}
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
