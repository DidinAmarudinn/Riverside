import { Suspense } from "react";
import type { Metadata } from "next";
import { ManagerDashboard } from "./manager-dashboard";
import { LoadingBlock } from "@/components/common/states";

export const metadata: Metadata = {
  title: "Manager Dashboard",
  description:
    "KPIs, ranked reorder recommendations, live demand signals and real-time alerts for store managers.",
};

export default function ManagerPage() {
  return (
    <Suspense fallback={<LoadingBlock label="Memuat dashboard…" />}>
      <ManagerDashboard />
    </Suspense>
  );
}
