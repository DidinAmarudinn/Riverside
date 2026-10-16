"use client";

import { useRouter } from "next/navigation";
import { TriangleAlert } from "lucide-react";
import type { Recommendation } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
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
      <table className="w-full min-w-[860px] text-left">
        <thead>
          <tr className="bg-surface-container-low text-on-surface-variant">
            <th className="rounded-l-lg px-3 py-2.5">
              <input
                type="checkbox"
                aria-label="Select all"
                className="h-4 w-4 cursor-pointer accent-primary"
                disabled
              />
            </th>
            <th className="px-3 py-2.5 text-table-header font-medium">
              SKU Name
            </th>
            <th className="px-3 py-2.5 text-table-header font-medium">
              Risk Status
            </th>
            <th className="px-3 py-2.5 text-right text-table-header font-medium">
              On Hand
            </th>
            <th className="px-3 py-2.5 text-right text-table-header font-medium">
              Forecast A
              <span className="block text-[10px] font-normal text-outline">
                POS only
              </span>
            </th>
            <th className="px-3 py-2.5 text-right text-table-header font-medium">
              Forecast B
              <span className="block text-[10px] font-normal text-primary">
                POS + Unmet
              </span>
            </th>
            <th className="px-3 py-2.5 text-right text-table-header font-medium">
              Rec. Qty
            </th>
            <th className="rounded-r-lg px-3 py-2.5 text-table-header font-medium">
              Reason &amp; Root Cause
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-container-low">
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
                  isHero && "bg-surface-container-low/60",
                )}
              >
                <td className="px-3 py-3.5">
                  <input
                    type="checkbox"
                    aria-label={`Select ${rec.name}`}
                    className="h-4 w-4 cursor-pointer accent-primary"
                    onClick={(e) => e.stopPropagation()}
                    disabled
                  />
                </td>
                <td className="px-3 py-3.5">
                  <div className="flex flex-col">
                    <span className="flex items-center gap-1.5 text-body-medium text-on-surface">
                      {rec.name}
                      {rec.riskType === "stockout_risk" ? (
                        <TriangleAlert
                          className="h-[14px] w-[14px] text-error"
                          aria-label="Zero stockout priority"
                        />
                      ) : null}
                    </span>
                    <span className="font-label-mono text-caption text-on-surface-variant">
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
                  {formatNumber(rec.forecastA)}
                </td>
                <td className="px-3 py-3.5 text-right font-semibold tabular-nums text-primary">
                  {formatNumber(rec.forecastB)}
                </td>
                <td className="px-3 py-3.5 text-right tabular-nums">
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 font-semibold",
                      isHero
                        ? "bg-primary-fixed text-on-primary-fixed"
                        : "bg-surface-container text-on-surface",
                    )}
                  >
                    {formatNumber(rec.recommendedQty)}
                  </span>
                </td>
                <td className="px-3 py-3.5 text-caption text-on-surface">
                  {rec.reasonText}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
