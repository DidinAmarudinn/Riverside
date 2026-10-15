import type { z } from "zod";
import type {
  AlertItem,
  DemoState,
  GapsResponse,
  KioskMessageResponse,
  LiveSignal,
  ManagerChatResponse,
  Metrics,
  Overview,
  Product,
  Recommendation,
  SkuDetail,
  Store,
} from "./types";
import {
  alertSchema,
  demoStateSchema,
  gapsSchema,
  kioskMessageSchema,
  liveSignalSchema,
  managerChatSchema,
  metricsSchema,
  overviewSchema,
  productSchema,
  recommendationSchema,
  skuDetailSchema,
  storeSchema,
} from "./schemas";

type Raw<T extends z.ZodType> = z.infer<T>;

export function adaptStore(raw: Raw<typeof storeSchema>): Store {
  const { storeId, ...rest } = raw;
  return { id: storeId, ...rest };
}

export function adaptProduct(raw: Raw<typeof productSchema>): Product {
  return raw;
}

export function adaptKioskMessage(
  raw: Raw<typeof kioskMessageSchema>,
): KioskMessageResponse {
  return { ...raw, nearestBranch: raw.nearestBranch ?? undefined };
}

export function adaptRecommendation(
  raw: Raw<typeof recommendationSchema>,
): Recommendation {
  return {
    storeId: raw.storeId,
    sku: raw.sku,
    name: raw.name,
    category: raw.category,
    onHand: raw.onHand,
    forecastA: raw.forecastA7d,
    forecastB: raw.forecastB7d,
    unmet7d: raw.unmet7d,
    recommendedQty: raw.recommendedQtyB,
    recommendedQtyA: raw.recommendedQtyA,
    riskType: raw.riskType,
    lostRevenueIdr: raw.lostRevenueIdr,
    reasonText: raw.reasonText,
  };
}

export function adaptMetrics(
  storeId: string,
  raw: Raw<typeof metricsSchema>,
): Metrics {
  return { storeId, ...raw };
}

export function adaptOverview(raw: Raw<typeof overviewSchema>): Overview {
  return {
    metrics: adaptMetrics(raw.storeId, raw.kpis),
    topRisks: raw.topRisks.map(adaptRecommendation),
  };
}

export function adaptAlert(raw: Raw<typeof alertSchema>): AlertItem {
  return raw;
}

/** Returns null for low_confidence signals, which are never shown as demand. */
export function adaptSignal(
  storeId: string,
  raw: Raw<typeof liveSignalSchema>,
): LiveSignal | null {
  if (raw.outcome === "low_confidence") return null;
  return {
    ...raw,
    storeId: raw.storeId ?? storeId,
    sku: raw.sku ?? undefined,
    outcome: raw.outcome,
  };
}

export function adaptManagerChat(
  raw: Raw<typeof managerChatSchema>,
): ManagerChatResponse {
  return raw;
}

export function adaptSkuDetail(raw: Raw<typeof skuDetailSchema>): SkuDetail {
  const { unmetDaily, recommendation, ...rest } = raw;
  const { recommendedQtyB, ...recRest } = recommendation;
  return {
    ...rest,
    dailyUnmet: unmetDaily,
    recommendation: { recommendedQty: recommendedQtyB, ...recRest },
  };
}

export function adaptGaps(raw: Raw<typeof gapsSchema>): GapsResponse {
  return raw;
}

export function adaptDemoState(raw: Raw<typeof demoStateSchema>): DemoState {
  return { scenario: raw.scenario, lastResetAt: raw.lastResetAt };
}
