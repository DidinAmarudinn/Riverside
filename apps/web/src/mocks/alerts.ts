import type { AlertItem } from "@/lib/api/types";

const MINUTE = 60 * 1000;

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * MINUTE).toISOString();
}

export const seedAlerts: AlertItem[] = [
  {
    id: "alert-oil-spike",
    storeId: "store_1",
    type: "unmet_spike",
    severity: "medium",
    title: "Unmet demand spike: Cooking oil category inquiries +140%",
    body: "Driven by evening promotional flier distribution.",
    createdAt: minutesAgo(42),
  },
  {
    id: "alert-beras-delay",
    storeId: "store_1",
    sku: "SKU-BRS5",
    type: "reorder",
    severity: "low",
    title: "Supplier delivery delayed: Beras distributor rescheduling to tomorrow",
    body: "ETA 08:00 WIB morning replenishment window.",
    createdAt: minutesAgo(88),
  },
  {
    id: "alert-kecap-overstock",
    storeId: "store_1",
    sku: "SKU-KCP5",
    type: "overstock",
    severity: "low",
    title: "Overstock watch: Kecap Manis Refill 550ml above 14-day cover",
    body: "Low velocity; substitute chosen in 92% of inquiries.",
    createdAt: minutesAgo(140),
  },
];

export const heroAlert: AlertItem = {
  id: "alert-santan-stockout",
  storeId: "store_1",
  sku: "SKU-65ML",
  type: "stockout_risk",
  severity: "critical",
  title: "Critical stockout on Santan Kotak 65 ml",
  body: "38 shopper requests logged while on-hand was 0. Forecast B = 60.",
  createdAt: new Date().toISOString(),
};
