"use client";

import Link from "next/link";
import type { Recommendation } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

/**
 * The one decision the dashboard should lead with: the product where adding the shoppers who asked
 * changes the order the most (largest B - A). Hidden when no recommendation differs.
 */
export function DecisionBanner({ recommendations }: { recommendations: Recommendation[] }) {
  const top = [...recommendations]
    .filter((r) => r.recommendedQty > r.recommendedQtyA)
    .sort((a, b) => b.recommendedQty - b.recommendedQtyA - (a.recommendedQty - a.recommendedQtyA))[0];
  if (!top) return null;

  return (
    <div className="grid grid-cols-1 items-center gap-5 rounded-xl bg-primary p-6 text-white/80 lg:grid-cols-[minmax(0,1fr)_auto]">
      <div className="min-w-0">
        <span className="text-caption font-semibold text-primary-fixed">
          Decision for today
        </span>
        <h2 className="mt-1 text-[22px] font-medium leading-tight tracking-[-0.02em] text-white sm:text-[28px]">
          {top.name}: order {formatNumber(top.recommendedQty)}, not {formatNumber(top.recommendedQtyA)}
        </h2>
        <p className="mt-1 max-w-2xl text-body-default text-white/70">
          {top.onHand === 0 ? "Out of stock. " : `${formatNumber(top.onHand)} on hand. `}
          {formatNumber(top.unmet7d)} shoppers asked for it at the kiosk in the last 7 days. Sales
          data alone missed them.
        </p>
      </div>
      <div className="flex flex-wrap items-stretch gap-3">
        <div className="rounded-lg bg-white/10 px-4 py-3 text-white">
          <span className="block text-caption text-white/70">Sales only (A)</span>
          <span className="text-[34px] font-medium leading-tight tracking-[-0.03em] tabular-nums">{top.recommendedQtyA}</span>
        </div>
        <div className="rounded-lg bg-primary-fixed px-4 py-3 text-on-primary-fixed">
          <span className="block text-caption">Demand Radar (B)</span>
          <span className="text-[34px] font-medium leading-tight tracking-[-0.03em] tabular-nums">{top.recommendedQty}</span>
        </div>
        <Link
          href={`/manager/sku?code=${encodeURIComponent(top.sku)}`}
          className="flex items-center self-center rounded-full bg-primary-fixed px-5 py-3 text-body-medium font-semibold text-on-primary-fixed transition hover:brightness-95"
        >
          See why →
        </Link>
      </div>
    </div>
  );
}
