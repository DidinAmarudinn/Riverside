"use client";

import { useSkuDetail } from "@/hooks/use-data";
import { formatDateWib, formatNumber } from "@/lib/format";
import { DemandBars } from "@/components/charts/demand-bars";

const HERO_SKU = "SKU-0001"; // Santan Kotak Kara 65 ml (data/seed_scenarios.yaml hero_santan)

/**
 * The problem in one card, from the live API: daily POS sales, then a run of zero days while shoppers
 * kept asking (one lime dot per request), and the reorder each forecast leads to.
 */
export function HeroStory() {
  const { data } = useSkuDetail(HERO_SKU);

  if (!data) {
    return <div className="min-h-[420px] animate-pulse rounded-xl bg-surface-container-lowest" aria-hidden />;
  }

  const asked = data.kpis.unmetRequests;
  const history = data.series.filter((p) => p.posSales != null).slice(-42);

  return (
    <div className="flex min-w-0 flex-col gap-4 rounded-xl bg-surface-container-lowest p-6 sm:p-7">
      <div className="flex flex-col gap-1">
        <span className="text-caption text-on-surface-variant">{data.name} · Radar Mart Cipete</span>
        <h2 className="text-[22px] font-medium leading-tight tracking-[-0.02em] text-on-surface sm:text-[26px]">
          The till saw 0 sold.{" "}
          <span className="rounded-lg bg-primary-fixed px-2">{formatNumber(asked)} shoppers asked.</span>
        </h2>
      </div>

      <DemandBars
        days={history.map((p) => ({
          date: p.date,
          sold: p.posSales ?? 0,
          asked: data.dailyUnmet.find((u) => u.date === p.date)?.count ?? 0,
        }))}
        label={`Daily sales of ${data.name}, then ${data.kpis.stockoutDays} days at zero while ${asked} shoppers asked for it`}
      />
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-caption text-on-surface-variant">
        <Legend swatch="bg-primary rounded-[3px]">units sold (POS)</Legend>
        <Legend swatch="bg-primary-fixed rounded-full">a shopper asked at the kiosk</Legend>
        <Legend swatch="bg-surface-container-high rounded-[3px]">
          sold out since {data.kpis.stockoutSince ? formatDateWib(data.kpis.stockoutSince) : "—"}, POS = 0
        </Legend>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-surface-container-low p-4">
          <span className="block text-caption text-on-surface">Sales only orders</span>
          <span className="block text-[40px] font-medium leading-tight tracking-[-0.03em] tabular-nums text-on-surface">
            {data.recommendation.recommendedQtyA}
          </span>
          <span className="text-caption text-on-surface-variant">units, next 7 days</span>
        </div>
        <div className="rounded-lg bg-primary-fixed p-4 text-on-primary-fixed">
          <span className="block text-caption">Demand Radar orders</span>
          <span className="block text-[40px] font-medium leading-tight tracking-[-0.03em] tabular-nums">
            {data.recommendation.recommendedQty}
          </span>
          <span className="text-caption opacity-75">units, next 7 days</span>
        </div>
      </div>
    </div>
  );
}

function Legend({ swatch, children }: { swatch: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block h-2.5 w-2.5 ${swatch}`} />
      {children}
    </span>
  );
}
