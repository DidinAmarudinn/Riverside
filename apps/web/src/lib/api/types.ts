/**
 * Domain types used across the UI. All names are camelCase.
 * Payloads follow docs/api-contract.md; mapping to these types happens in
 * src/lib/api/adapters.ts only.
 */

export type RiskType =
  | "stockout_risk"
  | "overstock"
  | "reorder"
  | "unmet_spike";

export type Outcome =
  | "purchased"
  | "out_of_stock"
  | "not_carried"
  | "substituted";

export interface Store {
  id: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
}

export interface Product {
  sku: string;
  name: string;
  brand: string;
  category: string;
  packSize?: string;
  unit?: string;
  priceIdr: number;
  aisle?: string;
  synonyms?: string[];
  isCarried: boolean;
  inStock?: boolean;
  stockQty?: number;
}

export interface KioskProductCard {
  sku: string;
  name: string;
  subtitle?: string;
  priceIdr?: number;
  inStock: boolean;
  aisle?: string;
  stockQty?: number;
}

export interface KioskBranchCard {
  storeId: string;
  name: string;
  distanceKm: number;
  stockQty: number;
}

export interface KioskMessageResponse {
  reply: string;
  products: KioskProductCard[];
  alternatives: KioskProductCard[];
  nearestBranch?: KioskBranchCard;
}

export interface Recommendation {
  storeId: string;
  sku: string;
  name: string;
  category: string;
  onHand: number;
  forecastA: number;
  forecastB: number;
  unmet7d: number;
  recommendedQty: number;
  recommendedQtyA: number;
  riskType: RiskType;
  lostRevenueIdr: number;
  reasonText: string;
}

export interface AlertItem {
  id: string;
  storeId: string;
  sku?: string;
  type: RiskType;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  body: string;
  createdAt: string;
}

export interface LiveSignal {
  id: string;
  storeId: string;
  ts: string;
  requestedText: string;
  sku?: string;
  matchedName?: string;
  substituteName?: string;
  outcome: Outcome;
  source?: string;
}

export interface Metrics {
  storeId: string;
  lostRevenueToday: number;
  unmetToday: number;
  stockoutSkus: number;
  posRefreshedAt?: string;
}

export interface Overview {
  metrics: Metrics;
  topRisks: Recommendation[];
}

/** One day on the SKU chart; null where a series has no value that day. */
export interface ForecastPoint {
  date: string;
  posSales: number | null;
  forecastA: number | null;
  forecastALower?: number;
  forecastAUpper?: number;
  forecastB: number | null;
  forecastBLower?: number;
  forecastBUpper?: number;
  isStockout: boolean;
}

export interface UnmetPoint {
  date: string;
  count: number;
}

export interface EvidenceItem {
  id: string;
  ts: string;
  channel: string;
  text: string;
  matchedName?: string;
  outcome: Outcome;
  confidence: number;
  intent?: string;
  highlight?: boolean;
}

export interface SkuRecommendation {
  recommendedQty: number;
  recommendedQtyA: number;
  reasonText: string;
  vendor?: string;
  leadTimeDays?: number;
  urgency?: "low" | "medium" | "high";
}

export interface SkuKpis {
  onHand: number;
  onHandNote?: string;
  lostRevenueIdr: number;
  lostRevenueUnits?: number;
  /** Over the running stockout (unmetWindowDays long), else the last 7 days. */
  unmetRequests: number;
  unmetWindowDays?: number;
  unmetRequests7d?: number;
  stockoutDays: number;
  stockoutSince?: string;
}

export interface SkuDetail {
  sku: string;
  name: string;
  brand?: string;
  category: string;
  barcode?: string;
  priceIdr: number;
  riskType: RiskType;
  kpis: SkuKpis;
  series: ForecastPoint[];
  dailyUnmet: UnmetPoint[];
  recommendation: SkuRecommendation;
  evidence: { total: number; items: EvidenceItem[] };
}

export interface Citation {
  label: string;
  sku?: string;
  date?: string;
  quote?: string;
}

export interface ManagerChatResponse {
  sessionId: string;
  reply: string;
  citations: Citation[];
}

export interface GapItem {
  rank: number;
  name: string;
  subtitle?: string;
  category: string;
  requests: number;
  trend7d: string;
  trendDirection: "up" | "down" | "flat";
  spark: number[];
  quote: string;
}

export interface GapCategory {
  name: string;
  count: number;
  percent: number;
}

export interface GapsResponse {
  items: GapItem[];
  summary: {
    totalRequests: number;
    lostRevenueExposureIdr: number;
    categories: GapCategory[];
  };
}

export interface DemoState {
  scenario: string;
  lastResetAt?: string;
}

export interface EvidenceDrawerTarget {
  sku: string;
  highlightId?: string;
}
