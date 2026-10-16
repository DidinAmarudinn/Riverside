import { Suspense } from "react";
import type { Metadata } from "next";
import { ManagerDashboard } from "./manager-dashboard";
import { DashboardSkeleton } from "@/components/manager/page-skeletons";

export const metadata: Metadata = {
  title: "Manager Dashboard",
  description:
    "KPIs, ranked reorder recommendations, live demand signals and real-time alerts for store managers.",
};

export default function ManagerPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <ManagerDashboard />
    </Suspense>
  );
}
