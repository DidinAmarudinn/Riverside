"use client";

import { useRouter } from "next/navigation";
import { TriangleAlert } from "lucide-react";
import type { Recommendation } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

/** Forecast units with one decimal at most, e.g. 2.6 (English separators like the rest of the manager pages). */
function formatQty(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 1 });
}
import { cn } from "@/lib/utils";
import { RiskBadge } from "./risk-badge";

export function RecommendationsTable({
  recommendations,
}: {
  recommendations: Recommendation[];
}) {
  const router = useRouter();

  return (
    <div className="-mx-6 overflow-x-auto px-6">
      <table className="w-full min-w-[760px] text-left">
        <thead>
          <tr className="border-b border-outline-variant text-on-surface-variant">
            <th className="px-3 py-2.5 text-caption font-medium">
              Product
            </th>
            <th className="px-3 py-2.5 text-caption font-medium">
              Risk
            </th>
            <th className="px-3 py-2.5 text-right text-caption font-medium">
              On Hand
            </th>
            <th className="px-3 py-2.5 text-right text-caption font-medium">
              Forecast A, 7 days
              <span className="block text-[10px] font-normal text-outline">
                POS only
              </span>
            </th>
            <th className="px-3 py-2.5 text-right text-caption font-medium">
              Forecast B, 7 days
              <span className="block text-[10px] font-normal text-primary-container">
                POS + Unmet
              </span>
            </th>
            <th className="px-3 py-2.5 text-right text-caption font-medium">
              Order
              <span className="block text-[10px] font-normal text-outline">
                A → B
              </span>
            </th>
            <th className="rounded-r-lg px-3 py-2.5 text-caption font-medium">
              Why
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant">
          {recommendations.map((rec) => {
            const isHero = rec.sku === "SKU-0001";
            return (
              <tr
                key={rec.sku}
                onClick={() =>
                  router.push(`/manager/sku?code=${encodeURIComponent(rec.sku)}`)
                }
                className={cn(
                  "cursor-pointer transition-colors hover:bg-surface-container-low",
                  isHero && "bg-secondary-fixed/50",
                )}
              >
                <td className="px-3 py-3.5">
                  <div className="flex flex-col">
                    <span className="flex items-center gap-1.5 text-body-medium text-on-surface">
                      {rec.name}
                      {rec.riskType === "stockout_risk" ? (
                        <TriangleAlert
                          className="h-[14px] w-[14px] text-error"
                          aria-label="Stockout risk"
                        />
                      ) : null}
                    </span>
                    <span className="text-caption text-on-surface-variant">
                      {rec.category}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-3.5">
                  <RiskBadge risk={rec.riskType} />
                </td>
                <td
                  className={cn(
                    "px-3 py-3.5 text-right tabular-nums",
                    rec.onHand <= 2 ? "font-semibold text-error" : "text-on-surface",
                  )}
                >
                  {formatNumber(rec.onHand)}
                </td>
                <td className="px-3 py-3.5 text-right tabular-nums text-outline">
                  {formatQty(rec.forecastA)}
                </td>
                <td className="px-3 py-3.5 text-right font-semibold tabular-nums text-primary-container">
                  {formatQty(rec.forecastB)}
                </td>
                <td className="whitespace-nowrap px-3 py-3.5 text-right tabular-nums">
                  {rec.recommendedQtyA !== rec.recommendedQty ? (
                    <span className="mr-1.5 text-caption text-outline line-through decoration-outline/60">
                      {formatNumber(rec.recommendedQtyA)}
                    </span>
                  ) : null}
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 font-semibold",
                      isHero ? "bg-primary-fixed text-on-primary-fixed" : "text-on-surface",
                    )}
                  >
                    {formatNumber(rec.recommendedQty)}
                  </span>
                </td>
                <td className="max-w-[320px] px-3 py-3.5 text-caption text-on-surface">
                  <span className="line-clamp-3" title={rec.reasonText}>
                    {rec.reasonText}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
