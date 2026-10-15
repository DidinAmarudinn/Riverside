"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Banknote,
  Download,
  Grid2x2,
  PackageX,
  ShoppingCart,
  Timer,
  TrendingUp,
} from "lucide-react";
import { useSkuDetail } from "@/hooks/use-data";
import { CardSkeleton, ErrorState } from "@/components/common/states";
import { RiskBadge } from "@/components/manager/risk-badge";
import { RecommendationCard } from "@/components/sku/recommendation-card";
import { EvidenceDrawer } from "@/components/sku/evidence-drawer";
import { Button } from "@/components/ui/button";
import { formatNumber, formatRupiah } from "@/lib/format";
import { cn } from "@/lib/utils";

const ForecastChart = dynamic(
  () => import("@/components/sku/forecast-chart"),
  { ssr: false, loading: () => <CardSkeleton rows={5} /> },
);
const UnmetChart = dynamic(() => import("@/components/sku/unmet-chart"), {
  ssr: false,
  loading: () => <CardSkeleton rows={3} />,
});

function Kpi({
  label,
  value,
  suffix,
  note,
  tone = "neutral",
  icon: Icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  note: string;
  tone?: "neutral" | "error" | "tertiary" | "primary";
  icon: React.ComponentType<{ className?: string }>;
}) {
  const toneClass =
    tone === "error"
      ? "text-error"
      : tone === "tertiary"
        ? "text-tertiary-container"
        : tone === "primary"
          ? "text-primary-container"
          : "text-on-surface";
  return (
    <div className="flex flex-col justify-between rounded-xl bg-surface-container-lowest p-4 shadow-sm">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-microcopy-caps uppercase tracking-wider text-on-surface-variant">
          {label}
        </span>
        <span
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-lg",
            tone === "error"
              ? "bg-error-container text-on-error-container"
              : "bg-surface-container-high text-primary-container",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      <div className="my-1 flex items-baseline gap-1.5">
        <span className={cn("text-kpi-stat", toneClass)}>{value}</span>
        {suffix ? (
          <span className="text-headline-sm font-normal text-on-surface-variant">
            {suffix}
          </span>
        ) : null}
      </div>
      <span className={cn("text-caption", toneClass)}>{note}</span>
    </div>
  );
}

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
        <p className="text-headline-md text-on-surface">SKU tidak dipilih</p>
        <p className="mt-1 text-caption text-on-surface-variant">
          Buka detail dari tabel rekomendasi.
        </p>
        <Link href="/manager" className="mt-4 inline-block">
          <Button variant="outline" size="sm">
            Kembali ke dashboard
          </Button>
        </Link>
      </div>
    );
  }

  if (isLoading) return <CardSkeleton rows={8} />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Gagal memuat detail SKU"
        description={`SKU ${code} tidak ditemukan atau respons tidak valid.`}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 pt-4">
        <div className="flex items-center gap-1 text-caption">
          <Link
            href="/manager"
            className="flex items-center gap-1 text-on-surface-variant transition-colors hover:text-primary-container"
          >
            <Grid2x2 className="h-[15px] w-[15px]" aria-hidden />
            Manager
          </Link>
          <span className="font-label-mono text-outline-variant">/</span>
          <span className="text-body-medium text-on-surface">{data.name}</span>
          <span className="ml-2 rounded bg-surface-container px-2 py-0.5 font-label-mono text-[11px] text-on-surface-variant">
            WIB Shifts Active
          </span>
        </div>

        <div className="flex flex-col justify-between gap-4 rounded-xl bg-surface-container-lowest p-6 shadow-sm lg:flex-row lg:items-center">
          <div className="flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-headline-lg tracking-tight text-on-surface">
                {data.name}
              </h1>
              <RiskBadge risk={data.riskType} />
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-on-surface-variant">
              <span className="text-body-medium text-on-surface">
                {data.category}
              </span>
              <span className="text-outline-variant">•</span>
              <span className="font-label-mono">SKU #{data.sku}</span>
              {data.barcode ? (
                <>
                  <span className="text-outline-variant">•</span>
                  <span className="font-label-mono">Barcode: {data.barcode}</span>
                </>
              ) : null}
              <span className="text-outline-variant">•</span>
              <span className="font-label-mono font-medium text-on-surface">
                Unit Price: {formatRupiah(data.priceIdr)}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="outline" size="md" disabled title="Segera hadir">
              <Download className="h-[18px] w-[18px]" aria-hidden />
              Export telemetry
            </Button>
            <Button variant="primary" size="md" disabled title="Segera hadir">
              <ShoppingCart className="h-[18px] w-[18px]" aria-hidden />
              Create PO ({data.recommendation.recommendedQty} units)
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label="Current On Hand"
          value={formatNumber(data.kpis.onHand)}
          suffix="units"
          note={data.kpis.onHandNote ?? "—"}
          tone={data.kpis.onHand <= 2 ? "error" : "neutral"}
          icon={PackageX}
        />
        <Kpi
          label="Lost Revenue (5d)"
          value={formatRupiah(data.kpis.lostRevenueIdr)}
          note={`${formatNumber(data.kpis.lostRevenueUnits ?? 0)} units missed`}
          tone="error"
          icon={Banknote}
        />
        <Kpi
          label="Unmet Requests (5d)"
          value={formatNumber(data.kpis.unmetRequests)}
          suffix="shoppers"
          note="Kiosk & voice signals"
          tone="tertiary"
          icon={TrendingUp}
        />
        <Kpi
          label="Stockout Duration"
          value={formatNumber(data.kpis.stockoutDays)}
          suffix="consecutive days"
          note={
            data.kpis.stockoutSince
              ? `Since ${new Date(data.kpis.stockoutSince).toLocaleDateString("id-ID")}`
              : "Currently in stock"
          }
          tone="neutral"
          icon={Timer}
        />
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="flex flex-col gap-6 lg:col-span-8">
          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6 shadow-sm">
            <div className="mb-2 flex flex-col justify-between gap-2 md:flex-row md:items-center">
              <div>
                <h2 className="text-headline-md text-on-surface">
                  30-Day Demand &amp; Sales Trajectory
                </h2>
                <p className="mt-0.5 text-caption text-on-surface-variant">
                  Daily POS units sold against machine-learned shopper demand
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-caption text-on-surface-variant">
                <span className="flex items-center gap-1.5">
                  <span className="h-3 w-3.5 rounded-sm bg-surface-container-high" />
                  POS Sales
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-0.5 w-4 border-t-2 border-dashed border-outline-variant" />
                  Forecast A (POS only)
                </span>
                <span className="flex items-center gap-1.5 font-medium text-primary-container">
                  <span className="h-1 w-4 rounded bg-primary-container" />
                  Forecast B (POS + unmet)
                </span>
              </div>
            </div>
            <ForecastChart data={data.series} />
            <div className="mt-3 flex items-start gap-2 rounded-lg bg-surface-container-low p-3 text-caption text-on-surface-variant">
              <TrendingUp className="mt-0.5 h-[18px] w-[18px] shrink-0 text-primary-container" aria-hidden />
              <p>
                Traditional ERP auto-reorder formulas read stockout zero-sales as
                tapering interest, dropping replenishment to 0.{" "}
                <strong className="font-medium text-on-surface">
                  Demand Radar corrects this distortion
                </strong>{" "}
                by blending conversational queries into SKU velocity.
              </p>
            </div>
          </div>

          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6 shadow-sm">
            <div className="mb-2 flex items-center justify-between">
              <div>
                <h3 className="text-headline-md text-on-surface">
                  Unmet Shopper Requests per Day
                </h3>
                <p className="mt-0.5 text-caption text-on-surface-variant">
                  Voice queries &amp; terminal searches logged while on-hand was 0
                </p>
              </div>
              <div className="text-right">
                <span className="text-kpi-stat-mobile text-tertiary-container">
                  {formatNumber(data.kpis.unmetRequests)}
                </span>
                <span className="block text-caption text-on-surface-variant">
                  Last 5 days
                </span>
              </div>
            </div>
            <UnmetChart data={data.dailyUnmet} />
          </div>
        </div>

        <div className="flex flex-col gap-6 lg:col-span-4">
          <RecommendationCard
            recommendation={data.recommendation}
            onViewEvidence={() => setManualOpen(true)}
          />

          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-4 shadow-sm">
            <div className="mb-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-headline-md text-on-surface">Evidence</h3>
                <span className="rounded-full bg-secondary-container px-2 py-0.5 font-label-mono text-[11px] font-bold text-on-secondary-fixed">
                  {data.evidence.total} conversations
                </span>
              </div>
            </div>
            <p className="mb-3 text-caption text-on-surface-variant">
              Verbatim quotes that justify the forecast.
            </p>
            <div className="flex flex-col gap-2">
              {data.evidence.items.slice(0, 3).map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg bg-surface-container-low p-2.5 text-caption italic text-on-surface"
                >
                  “{item.text}”
                </div>
              ))}
            </div>
            <Button
              variant="secondary"
              className="mt-3"
              onClick={() => setManualOpen(true)}
            >
              Buka evidence drawer
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
      {highlight ? <span className="sr-only">Highlight {highlight}</span> : null}
    </div>
  );
}
