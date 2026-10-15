"use client";

import { Sparkles, BadgeCheck } from "lucide-react";
import type { SkuRecommendation } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { env } from "@/lib/env";

export function RecommendationCard({
  recommendation,
  onViewEvidence,
}: {
  recommendation: SkuRecommendation;
  onViewEvidence: () => void;
}) {
  const urgency =
    recommendation.urgency === "high"
      ? "High Urgency"
      : recommendation.urgency === "medium"
        ? "Medium Urgency"
        : "Monitor";

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl bg-surface-container-lowest p-6 shadow-sm">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary-container via-secondary-container to-primary" />
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-surface-container-high text-primary-container">
            <Sparkles className="h-[15px] w-[15px]" aria-hidden />
          </span>
          <span className="font-microcopy-caps font-semibold uppercase tracking-wider text-on-surface">
            Recommended Action
          </span>
        </div>
        <span className="rounded-full bg-surface-container-low px-2 py-0.5 font-label-mono text-[11px] text-primary-container">
          AI Engine
        </span>
      </div>

      <div className="mb-4 rounded-xl bg-surface-container-low p-4">
        <div className="flex items-baseline justify-between">
          <span className="text-caption text-on-surface-variant">
            Suggested Replenishment
          </span>
          <span className="font-microcopy-caps font-medium uppercase text-tertiary">
            {urgency}
          </span>
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-kpi-stat-mobile text-primary-container">
            Order {recommendation.recommendedQty} units
          </span>
        </div>
        {recommendation.vendor ? (
          <div className="mt-3 flex items-center justify-between border-t border-surface-container pt-2 text-caption text-on-surface">
            <span className="text-on-surface-variant">Vendor:</span>
            <span className="text-body-medium">{recommendation.vendor}</span>
          </div>
        ) : null}
        {recommendation.leadTimeDays != null ? (
          <div className="mt-1 flex items-center justify-between text-caption text-on-surface">
            <span className="text-on-surface-variant">Lead Time:</span>
            <span className="font-label-mono font-medium text-primary-container">
              {recommendation.leadTimeDays} day
              {recommendation.leadTimeDays > 1 ? "s" : ""} (next morning shift)
            </span>
          </div>
        ) : null}
      </div>

      <p className="mb-5 text-body-default leading-relaxed text-on-surface">
        “{recommendation.reasonText}”
      </p>

      <div className="flex flex-col gap-2">
        {env.featureApprove ? (
          <Button variant="primary" disabled title="Segera hadir">
            <BadgeCheck className="h-[18px] w-[18px]" aria-hidden />
            Approve Order ({recommendation.recommendedQty} units)
          </Button>
        ) : null}
        <Button variant="secondary" onClick={onViewEvidence}>
          Lihat evidence
        </Button>
      </div>
    </div>
  );
}
