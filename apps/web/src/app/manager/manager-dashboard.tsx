"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw, TrendingDown, Radio, TriangleAlert } from "lucide-react";
import {
  useOverview,
  useRecommendations,
  useStores,
} from "@/hooks/use-data";
import { useAlerts, useLiveSignals, useMetrics } from "@/hooks/use-realtime";
import type { RiskType } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/common/states";
import { KpiCard } from "@/components/manager/kpi-card";
import { DecisionBanner } from "@/components/manager/decision-banner";
import { DecisionBannerSkeleton } from "@/components/manager/page-skeletons";
import { RecommendationsTable } from "@/components/manager/recommendations-table";
import { LiveFeed } from "@/components/manager/live-feed";
import { AlertsPanel } from "@/components/manager/alerts-panel";
import { AgentChat } from "@/components/manager/agent-chat";
import { StoreSelector } from "@/components/manager/store-selector";
import { useStore } from "@/hooks/use-store";
import { formatRupiah, formatTimeWib } from "@/lib/format";
import { env } from "@/lib/env";

const RISK_FILTERS: { value: RiskType | "all"; label: string }[] = [
  { value: "all", label: "All risks" },
  { value: "stockout_risk", label: "Stockout" },
  { value: "unmet_spike", label: "Unmet spike" },
  { value: "reorder", label: "Reorder" },
  { value: "overstock", label: "Overstock" },
];

export function ManagerDashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const riskParam = searchParams.get("risk") as RiskType | null;
  const prefillQuestion = searchParams.get("q") ?? undefined;
  const chatSku = searchParams.get("sku") ?? undefined;

  const overview = useOverview();
  const recommendations = useRecommendations(riskParam ?? undefined);
  const metrics = useMetrics();
  const alerts = useAlerts();
  const signals = useLiveSignals();
  const stores = useStores();
  const { storeId } = useStore();
  const storeName = stores.data?.find((s) => s.id === storeId)?.name ?? storeId;

  const effectiveMetrics = metrics ?? overview.data?.metrics ?? null;

  const [highlightAlert, setHighlightAlert] = useState<string | null>(null);
  const seenAlerts = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!alerts) return;
    const newest = alerts[0];
    if (!newest) return;
    if (seenAlerts.current.size > 0 && !seenAlerts.current.has(newest.id)) {
      setHighlightAlert(newest.id);
      const t = setTimeout(() => setHighlightAlert(null), 4000);
      return () => clearTimeout(t);
    }
    alerts.forEach((a) => seenAlerts.current.add(a.id));
  }, [alerts]);

  const setRiskFilter = (value: RiskType | "all") => {
    const params = new URLSearchParams(searchParams.toString());
    if (value === "all") params.delete("risk");
    else params.set("risk", value);
    params.delete("q");
    router.replace(`/manager?${params.toString()}`);
  };

  const tableState = useMemo(() => {
    if (recommendations.isLoading) return "loading" as const;
    if (recommendations.isError) return "error" as const;
    if (!recommendations.data?.length) return "empty" as const;
    return "ready" as const;
  }, [recommendations.isLoading, recommendations.isError, recommendations.data]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col justify-between gap-4 pt-2 md:flex-row md:items-center">
        <div className="flex flex-col">
          <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
            {storeName}
          </h1>
          <p className="mt-1 text-caption text-on-surface-variant">
            Unmet shopper demand from kiosk conversations next to POS sales. Simulated data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StoreSelector />
          {effectiveMetrics?.posRefreshedAt ? (
          <div className="flex items-center gap-2 rounded-full bg-surface-container-lowest px-4 py-2.5">
            <RefreshCw className="h-4 w-4 text-primary" aria-hidden />
            <span className="text-caption text-on-surface-variant">
              POS Refreshed:{" "}
              <span className="font-semibold text-on-surface">
                {formatTimeWib(effectiveMetrics.posRefreshedAt)} WIB
              </span>
            </span>
          </div>
          ) : null}
        </div>
      </div>

      {!riskParam && recommendations.isLoading ? (
        <DecisionBannerSkeleton />
      ) : !riskParam && recommendations.data?.length ? (
        <DecisionBanner recommendations={recommendations.data} />
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard
          label="Revenue lost today"
          value={effectiveMetrics ? formatRupiah(effectiveMetrics.lostRevenueToday) : ""}
          loading={!effectiveMetrics}
          tone="error"
          icon={TrendingDown}
          footerValue="Unmet × price"
          footerLabel="today"
        />
        <KpiCard
          label="Unmet requests today"
          value={effectiveMetrics ? String(effectiveMetrics.unmetToday) : ""}
          loading={!effectiveMetrics}
          suffix="requests"
          tone="primary"
          icon={Radio}
          footerValue="Kiosk chats"
          footerLabel="out of stock or not carried"
        />
        <KpiCard
          label="Out of stock now"
          value={effectiveMetrics ? String(effectiveMetrics.stockoutSkus) : ""}
          loading={!effectiveMetrics}
          suffix={effectiveMetrics?.stockoutSkus === 1 ? "product" : "products"}
          tone="warning"
          icon={TriangleAlert}
          footerValue="Zero on the shelf"
          footerLabel="see Recommendations"
        />
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <div className="flex flex-col gap-4 lg:col-span-8">
          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6">
            <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-headline-lg text-on-surface">
                    Recommendations
                  </span>
                </div>
                <p className="mt-0.5 text-caption text-on-surface-variant">
                  Reorder for the next 7 days, most at risk first
                </p>
              </div>
              {env.featureApprove ? (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled
                  title="Segera hadir"
                >
                  Approve Selected POs
                </Button>
              ) : null}
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              {RISK_FILTERS.map((f) => {
                const active = (riskParam ?? "all") === f.value;
                return (
                  <button
                    key={f.value}
                    type="button"
                    onClick={() => setRiskFilter(f.value)}
                    className={cn(
                      "rounded-full px-3.5 py-2 text-caption transition",
                      active
                        ? "bg-primary-fixed font-semibold text-on-primary-fixed"
                        : "bg-surface-container-low text-on-surface hover:bg-surface-container-high",
                    )}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>

            {tableState === "loading" ? (
              <CardSkeleton rows={6} />
            ) : tableState === "error" ? (
              <ErrorState
                description="Could not load recommendations."
                onRetry={() => recommendations.refetch()}
              />
            ) : tableState === "empty" ? (
              <EmptyState
                title="No recommendations yet"
                description="Try another risk filter."
              />
            ) : (
              <RecommendationsTable recommendations={recommendations.data ?? []} />
            )}

            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-surface-container pt-3 text-caption text-on-surface-variant">
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-outline" />
                  Forecast A: POS sales only
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-primary" />
                  Forecast B: POS + unmet kiosk demand
                </span>
              </div>
              <span className="font-label-mono">
                {recommendations.data?.length ?? 0} priority recommendations
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-4">
          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
                </span>
                <span className="text-headline-sm text-on-surface">
                  Live demand feed
                </span>
              </div>
              <span className="font-label-mono text-caption text-on-surface-variant">
                Kiosk signals
              </span>
            </div>
            {signals === null ? (
              <CardSkeleton rows={5} />
            ) : signals.length === 0 ? (
              <EmptyState
                title="No signals yet"
                description="Ask the kiosk for something out of stock; it shows up here within seconds."
              />
            ) : (
              <LiveFeed signals={signals} />
            )}
          </div>

          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-headline-sm text-on-surface">
                  Alerts
                </span>
                {alerts?.length ? (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-error text-[11px] font-bold text-on-error">
                    {alerts.length}
                  </span>
                ) : null}
              </div>
              <span className="text-caption font-medium text-primary">
                Real-time
              </span>
            </div>
            {alerts === null ? (
              <CardSkeleton rows={3} />
            ) : alerts.length === 0 ? (
              <EmptyState title="No alerts yet" />
            ) : (
              <AlertsPanel alerts={alerts} highlightId={highlightAlert} />
            )}
          </div>
        </div>
      </div>

      <div className="fixed bottom-6 right-6 z-40">
        <AgentChat initialQuestion={prefillQuestion} sku={chatSku} />
      </div>
    </div>
  );
}
