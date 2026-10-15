"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw, Sunrise, TrendingDown, Radio, TriangleAlert } from "lucide-react";
import {
  useNextMorning,
  useOverview,
  useRecommendations,
} from "@/hooks/use-data";
import { useAlerts, useLiveSignals, useMetrics } from "@/hooks/use-realtime";
import type { RiskType } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/common/states";
import { KpiCard } from "@/components/manager/kpi-card";
import { RecommendationsTable } from "@/components/manager/recommendations-table";
import { LiveFeed } from "@/components/manager/live-feed";
import { AlertsPanel } from "@/components/manager/alerts-panel";
import { AgentChat } from "@/components/manager/agent-chat";
import { StoreSelector } from "@/components/manager/store-selector";
import { formatRupiah, formatTimeWib } from "@/lib/format";

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
  const { toast } = useToast();

  const overview = useOverview();
  const recommendations = useRecommendations(riskParam ?? undefined);
  const metrics = useMetrics();
  const alerts = useAlerts();
  const signals = useLiveSignals();
  const nextMorning = useNextMorning();

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
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 pt-6 md:flex-row md:items-center">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-headline-lg tracking-tight text-on-surface">
              Toko 1 – Overview
            </span>
            <span className="rounded-full bg-surface-container-high px-2 py-0.5 font-label-mono text-caption text-primary">
              WIB Active Shift
            </span>
          </div>
          <p className="mt-1 text-caption text-on-surface-variant">
            Supermarket telemetry, floor voice queries &amp; POS reconciliation
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StoreSelector />
          <div className="flex items-center gap-2 rounded-xl bg-surface-container-lowest px-4 py-2 shadow-sm">
            <RefreshCw className="h-4 w-4 text-primary" aria-hidden />
            <span className="text-caption text-on-surface-variant">
              POS Refreshed:{" "}
              <span className="font-semibold text-on-surface">
                {effectiveMetrics?.posRefreshedAt
                  ? `${formatTimeWib(effectiveMetrics.posRefreshedAt)} WIB`
                  : "—"}
              </span>
            </span>
          </div>
          <Button
            variant="primary"
            onClick={() =>
              nextMorning.mutate(undefined, {
                onSuccess: () =>
                  toast({
                    title: "Rekomendasi dihitung ulang",
                    variant: "success",
                  }),
                onError: () =>
                  toast({
                    title: "Gagal menjalankan next morning",
                    variant: "error",
                  }),
              })
            }
            disabled={nextMorning.isPending}
          >
            <Sunrise className="h-4 w-4" aria-hidden />
            {nextMorning.isPending ? "Menghitung…" : "Next morning"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <KpiCard
          label="Revenue Lost Today"
          value={effectiveMetrics ? formatRupiah(effectiveMetrics.lostRevenueToday) : "—"}
          tone="error"
          icon={TrendingDown}
          footerValue="Unmet × price"
          footerLabel="today"
        />
        <KpiCard
          label="Unmet Requests Today"
          value={effectiveMetrics ? String(effectiveMetrics.unmetToday) : "—"}
          suffix="queries"
          tone="primary"
          icon={Radio}
          footerValue="Voice & Kiosk"
          footerLabel="in-store kiosks"
        />
        <KpiCard
          label="SKUs At Risk"
          value={effectiveMetrics ? String(effectiveMetrics.stockoutSkus) : "—"}
          suffix="critical lines"
          tone="warning"
          icon={TriangleAlert}
          footerValue="stockout_risk"
          footerLabel="needs action"
        />
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="flex flex-col gap-4 lg:col-span-8">
          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6 shadow-sm">
            <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-headline-md text-on-surface">
                    Recommendations
                  </span>
                  <span className="rounded-full bg-surface-container px-2 py-0.5 font-label-mono text-caption text-on-surface-variant">
                    Sorted by Risk
                  </span>
                </div>
                <p className="mt-0.5 text-caption text-on-surface-variant">
                  Actionable reorder adjustments combining POS and unmet demand
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                disabled
                title="Segera hadir"
              >
                Approve Selected POs
              </Button>
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
                      "rounded-full px-3 py-1 text-caption font-medium transition",
                      active
                        ? "bg-primary text-on-primary"
                        : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container",
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
                description="Gagal memuat rekomendasi."
                onRetry={() => recommendations.refetch()}
              />
            ) : tableState === "empty" ? (
              <EmptyState
                title="Tidak ada rekomendasi"
                description="Coba ubah filter risiko atau jalankan Next morning."
              />
            ) : (
              <RecommendationsTable recommendations={recommendations.data ?? []} />
            )}

            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-surface-container pt-3 text-caption text-on-surface-variant">
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-outline" />
                  Forecast A: Historical POS Run-rate
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-primary" />
                  Forecast B: True Demand (POS + Kiosk Intent)
                </span>
              </div>
              <span className="font-label-mono">
                {recommendations.data?.length ?? 0} priority recommendations
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-6 lg:col-span-4">
          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
                </span>
                <span className="text-headline-sm text-on-surface">
                  Live Demand Feed
                </span>
              </div>
              <span className="font-label-mono text-caption text-on-surface-variant">
                SCBD Terminals
              </span>
            </div>
            {signals === null ? (
              <CardSkeleton rows={5} />
            ) : signals.length === 0 ? (
              <EmptyState
                title="Belum ada sinyal"
                description="Sinyal muncul < 5 detik setelah percakapan kiosk."
              />
            ) : (
              <LiveFeed signals={signals} />
            )}
          </div>

          <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-headline-sm text-on-surface">
                  Alerts &amp; Notifications
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
              <EmptyState title="Tidak ada alert" />
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
