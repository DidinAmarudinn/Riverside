import { Suspense } from "react";
import type { Metadata } from "next";
import { SkuDetail } from "./sku-detail";
import { CardSkeleton } from "@/components/common/states";

export const metadata: Metadata = {
  title: "SKU Detail",
  description:
    "POS sales vs. Forecast A vs. Forecast B, daily unmet demand, recommendation and verbatim evidence for a single SKU.",
};

export default function SkuPage() {
  return (
    <Suspense fallback={<CardSkeleton rows={8} />}>
      <SkuDetail />
    </Suspense>
  );
}
