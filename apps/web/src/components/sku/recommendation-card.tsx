"use client";

import { BadgeCheck } from "lucide-react";
import type { SkuRecommendation } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { env } from "@/lib/env";

/** The decision side by side: what a sales-only forecast would order vs. what Demand Radar orders. */
export function RecommendationCard({
  recommendation,
}: {
  recommendation: SkuRecommendation;
}) {
  const qtyA = recommendation.recommendedQtyA;
  const qtyB = recommendation.recommendedQty;

  return (
    <div className="flex flex-col rounded-xl bg-surface-container-lowest p-6">
      <h3 className="text-headline-md text-on-surface">Reorder for the next 7 days</h3>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-surface-container-low p-4">
          <span className="block text-caption text-on-surface-variant">
            Sales only (A)
          </span>
          <span className="mt-1 block text-[40px] font-medium leading-tight tracking-[-0.03em] tabular-nums text-on-surface">
            {qtyA != null ? qtyA : "—"}
          </span>
          <span className="text-caption text-outline">units</span>
        </div>
        <div className="rounded-lg bg-primary-fixed p-4 text-on-primary-fixed">
          <span className="block text-caption opacity-90">Demand Radar (B)</span>
          <span className="mt-1 block text-[40px] font-medium leading-tight tracking-[-0.03em] tabular-nums">
            {qtyB}
          </span>
          <span className="text-caption opacity-90">units</span>
        </div>
      </div>

      {recommendation.leadTimeDays != null ? (
        <p className="mt-3 text-caption text-on-surface-variant">
          Lead time {recommendation.leadTimeDays} day
          {recommendation.leadTimeDays > 1 ? "s" : ""}.
        </p>
      ) : null}

      <div className="mt-4">
        <span className="block text-headline-sm text-on-surface">Why</span>
        <p className="mt-1 text-body-default leading-relaxed text-on-surface">
          {recommendation.reasonText}
        </p>
        <p className="mt-1 text-caption text-on-surface-variant">
          Written by Gemini from the numbers on this page.
        </p>
      </div>

      <div className="mt-5 flex flex-col gap-2">
        {env.featureApprove ? (
          <Button variant="primary" disabled title="Coming soon">
            <BadgeCheck className="h-[18px] w-[18px]" aria-hidden />
            Approve Order ({qtyB} units)
          </Button>
        ) : null}
      </div>
    </div>
  );
}
