import type { LiveSignal, Metrics } from "@/lib/api/types";

const MINUTE = 60 * 1000;

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * MINUTE).toISOString();
}

export const seedSignals: LiveSignal[] = [
  {
    id: "sig-1",
    storeId: "store_1",
    ts: minutesAgo(6),
    requestedText: "ada santan kotak kecil ga?",
    sku: "SKU-65ML",
    matchedName: "Santan Kotak 65 ml",
    outcome: "out_of_stock",
    source: "Voice Kiosk #02",
  },
  {
    id: "sig-2",
    storeId: "store_1",
    ts: minutesAgo(10),
    requestedText: "minyak goreng 2 liter ada promo?",
    sku: "SKU-MG2L",
    matchedName: "Minyak Goreng Sawit 2L",
    outcome: "purchased",
    source: "Kiosk Search #04",
  },
  {
    id: "sig-3",
    storeId: "store_1",
    ts: minutesAgo(23),
    requestedText: "biskuit kaleng matcha jepang",
    outcome: "not_carried",
    source: "Voice Kiosk #01",
  },
  {
    id: "sig-4",
    storeId: "store_1",
    ts: minutesAgo(36),
    requestedText: "santan kara sachet ada ga",
    sku: "SKU-2J4K",
    matchedName: "Santan Kotak 65 ml",
    substituteName: "Santan Bubuk Sachet 50g",
    outcome: "substituted",
    source: "Staff Barcode Assist",
  },
  {
    id: "sig-5",
    storeId: "store_1",
    ts: minutesAgo(48),
    requestedText: "gula pasir curah kiloan",
    sku: "SKU-GLP1",
    matchedName: "Gula Pasir Kristal Putih 1kg",
    outcome: "out_of_stock",
    source: "Voice Kiosk #03",
  },
];

export const initialMetrics: Metrics = {
  storeId: "store_1",
  lostRevenueToday: 1_980_000,
  unmetToday: 24,
  stockoutSkus: 6,
  posRefreshedAt: new Date().toISOString(),
};

export const heroMetrics: Metrics = {
  storeId: "store_1",
  lostRevenueToday: 2_340_000,
  unmetToday: 38,
  stockoutSkus: 7,
  posRefreshedAt: new Date().toISOString(),
};
