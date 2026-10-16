"use client";

import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { MessageSquareText, Package, Timer, TrendingDown } from "lucide-react";
import { useSkuDetail } from "@/hooks/use-data";
import { CardSkeleton, ErrorState } from "@/components/common/states";
import { RiskBadge } from "@/components/manager/risk-badge";
import { RecommendationCard } from "@/components/sku/recommendation-card";
import { EvidenceDrawer } from "@/components/sku/evidence-drawer";
import { Button } from "@/components/ui/button";
import { formatDateWib, formatNumber, formatRupiah, formatRupiahCompact } from "@/lib/format";
import { KpiCard } from "@/components/manager/kpi-card";
import { AgentChat } from "@/components/manager/agent-chat";
import { DemandBars } from "@/components/charts/demand-bars";

export function SkuDetail() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const openEvidence = searchParams.get("evidence") === "open";
  const highlight = searchParams.get("highlight") ?? undefined;

  const { data, isLoading, isError, refetch } = useSkuDetail(code);
  const [manualOpen, setManualOpen] = useState<boolean | null>(null);
  const drawerOpen = manualOpen ?? openEvidence;

  if (!code) {
    return (
      <div className="py-16 text-center">
        <p className="text-headline-md text-on-surface">No product selected</p>
        <p className="mt-1 text-caption text-on-surface-variant">
          Open a product from the recommendations table.
        </p>
        <Link href="/manager" className="mt-4 inline-block">
          <Button variant="outline" size="sm">
            Back to the dashboard
          </Button>
        </Link>
      </div>
    );
  }

  if (isLoading) return <CardSkeleton rows={8} />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Could not load this product"
        description={`SKU ${code} was not found or the response was invalid.`}
        onRetry={() => refetch()}
      />
    );
  }

  const unmetDays = data.kpis.unmetWindowDays ?? 7;
  const unmetLabel =
    data.kpis.stockoutDays > 0
      ? `During this ${unmetDays}-day stockout`
      : `Last ${unmetDays} days`;

  const history = data.series.filter((p) => p.posSales != null).slice(-42);
  const ahead = data.series.filter((p) => p.posSales == null && (p.forecastA != null || p.forecastB != null));
  const asked = new Map(data.dailyUnmet.map((u) => [u.date, u.count]));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3 pt-2">
        <div className="flex flex-col gap-1">
          <Link href="/manager" className="text-caption text-on-surface-variant hover:text-on-surface">
            Manager / Product
          </Link>
          <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
            {data.name}
          </h1>
          <p className="text-body-default text-on-surface-variant">
            {data.category} · {data.sku} · {formatRupiah(data.priceIdr)}
          </p>
        </div>
        <RiskBadge risk={data.riskType} className="px-3.5 py-2 text-body-default" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="On hand"
          value={formatNumber(data.kpis.onHand)}
          footerValue={data.kpis.onHand === 0 ? "empty shelf" : "units on the shelf"}
          icon={Package}
        />
        <KpiCard
          label="Stockout"
          value={data.kpis.stockoutDays ? `${formatNumber(data.kpis.stockoutDays)} days` : "None"}
          footerValue={data.kpis.stockoutSince ? `since ${formatDateWib(data.kpis.stockoutSince)}` : "currently in stock"}
          icon={Timer}
        />
        <KpiCard
          label="Shoppers asked"
          value={formatNumber(data.kpis.unmetRequests)}
          footerValue={unmetLabel.toLowerCase()}
          tone="lime"
          icon={MessageSquareText}
        />
        <KpiCard
          label="Lost, last 7 days"
          value={formatRupiahCompact(data.kpis.lostRevenueIdr)}
          footerValue={`≈${formatNumber(data.kpis.lostRevenueUnits ?? 0)} units, incl. shoppers who did not ask`}
          icon={TrendingDown}
        />
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <div className="flex min-w-0 flex-col gap-3 rounded-xl bg-surface-container-lowest p-6 lg:col-span-8">
          <div>
            <h2 className="text-headline-lg text-on-surface">Sales and forecast</h2>
            <p className="text-caption text-on-surface-variant">
              POS sales per day, then the next {ahead.length} days from forecast A and forecast B
            </p>
          </div>
          <DemandBars
            days={history.map((p) => ({ date: p.date, sold: p.posSales ?? 0, asked: asked.get(p.date) ?? 0 }))}
            forecast={ahead.map((p) => ({ date: p.date, a: p.forecastA, b: p.forecastB }))}
            height={240}
            label={`Daily sales of ${data.name}, shoppers who asked, and forecasts A and B`}
          />
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-caption text-on-surface-variant">
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-[3px] bg-primary" />POS sales</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-primary-fixed" />shoppers who asked</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-[3px] w-3 bg-outline" />forecast A (POS only)</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-[3px] w-3 bg-primary-container" />forecast B (POS + unmet)</span>
          </div>
          <p className="rounded-lg bg-surface-container-low p-3 text-caption text-on-surface-variant">
            While the shelf is empty the till records zero, so a sales-only forecast reads it as no demand.{" "}
            <strong className="font-semibold text-on-surface">Forecast B adds back the shoppers who asked</strong>,
            estimated from kiosk conversations.
          </p>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-4">
          <RecommendationCard recommendation={data.recommendation} />

          <div className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-headline-md text-on-surface">What shoppers typed</h3>
              <span className="rounded-full bg-surface-container-low px-2.5 py-1 text-caption text-on-surface-variant">
                {data.evidence.total} in total
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {data.evidence.items.slice(0, 3).map((item) => (
                <div key={item.id} className="rounded-xl bg-surface-container-low px-3.5 py-2.5 text-body-default italic text-on-surface">
                  “{item.text}”
                </div>
              ))}
            </div>
            <Button className="self-start" onClick={() => setManualOpen(true)}>
              See all conversations
            </Button>
          </div>
        </div>
      </div>

      <EvidenceDrawer
        open={drawerOpen}
        onOpenChange={setManualOpen}
        skuName={data.name}
        total={data.evidence.total}
        items={data.evidence.items}
      />
      <div className="fixed bottom-6 right-6 z-40">
        <AgentChat sku={data.sku} />
      </div>
      {highlight ? <span className="sr-only">Highlight {highlight}</span> : null}
    </div>
  );
}
