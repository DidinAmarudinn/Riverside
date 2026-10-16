import type { z } from "zod";
import type {
  AlertItem,
  DemoState,
  GapsResponse,
  KioskMessageResponse,
  LiveSignal,
  ForecastPoint,
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
  return {
    ...raw,
    citations: raw.citations.map((c) => ({
      label: c.label,
      sku: c.sku ?? undefined,
      date: c.date ?? undefined,
      quote: c.quote ?? undefined,
    })),
  };
}

/** Merges the separate sales / forecast A / forecast B series by date. */
function mergeSeries(raw: Raw<typeof skuDetailSchema>): ForecastPoint[] {
  const byDate = new Map<string, ForecastPoint>();
  const at = (date: string) => {
    let p = byDate.get(date);
    if (!p) {
      p = { date, posSales: null, forecastA: null, forecastB: null, isStockout: false };
      byDate.set(date, p);
    }
    return p;
  };
  for (const s of raw.sales) {
    const p = at(s.date);
    p.posSales = s.qty;
    p.isStockout = s.isStockout;
  }
  for (const f of raw.forecastA) {
    const p = at(f.date);
    p.forecastA = f.qty;
    p.forecastALower = f.lower ?? undefined;
    p.forecastAUpper = f.upper ?? undefined;
  }
  for (const f of raw.forecastB) {
    const p = at(f.date);
    p.forecastB = f.qty;
    p.forecastBLower = f.lower ?? undefined;
    p.forecastBUpper = f.upper ?? undefined;
  }
  return [...byDate.values()].sort((x, y) => x.date.localeCompare(y.date));
}

export function adaptSkuDetail(raw: Raw<typeof skuDetailSchema>): SkuDetail {
  const { product, kpis, reason } = raw;
  return {
    sku: raw.sku,
    name: product.name,
    brand: product.brand,
    category: product.category,
    priceIdr: product.priceIdr,
    riskType: raw.riskType,
    kpis: {
      onHand: kpis.onHand,
      lostRevenueIdr: kpis.lostRevenueIdr,
      lostRevenueUnits: kpis.lostRevenueUnits,
      unmetRequests: kpis.unmetRequests,
      unmetWindowDays: kpis.unmetWindowDays,
      unmetRequests7d: kpis.unmetRequests7d,
      stockoutDays: kpis.stockoutDays,
      stockoutSince: kpis.stockoutSince ?? undefined,
    },
    series: mergeSeries(raw),
    dailyUnmet: raw.unmetDaily,
    recommendation: {
      recommendedQty: reason.recommendedQtyB,
      recommendedQtyA: reason.recommendedQtyA,
      reasonText: reason.reasonText,
      leadTimeDays: reason.leadTimeDays ?? undefined,
      urgency:
        raw.riskType === "stockout_risk"
          ? "high"
          : raw.riskType === "unmet_spike"
            ? "medium"
            : "low",
    },
    evidence: {
      total: raw.evidence.total,
      items: raw.evidence.items.map(({ quote, ...e }) => ({ ...e, text: quote })),
    },
  };
}

function formatTrend(pct: number): string {
  const rounded = Math.round(pct);
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}

/** Ranks items and builds the per-category summary (contract §3.1 GapItem). */
export function adaptGaps(raw: Raw<typeof gapsSchema>): GapsResponse {
  const sorted = [...raw.items].sort((a, b) => b.requests - a.requests);
  const totalRequests = sorted.reduce((sum, g) => sum + g.requests, 0);
  const perCategory = new Map<string, number>();
  for (const g of sorted) {
    perCategory.set(g.category, (perCategory.get(g.category) ?? 0) + g.requests);
  }
  return {
    items: sorted.map((g, i) => ({
      rank: i + 1,
      name: g.name,
      category: g.category,
      requests: g.requests,
      trend7d: formatTrend(g.trend7dPct),
      trendDirection:
        g.trend7dPct > 0 ? "up" : g.trend7dPct < 0 ? "down" : "flat",
      spark: g.daily,
      quote: g.quote ?? "",
    })),
    summary: {
      totalRequests,
      lostRevenueExposureIdr: sorted.reduce(
        (sum, g) => sum + (g.estRevenueIdr ?? 0),
        0,
      ),
      categories: [...perCategory]
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => ({
          name,
          count,
          percent: totalRequests ? count / totalRequests : 0,
        })),
    },
  };
}

export function adaptDemoState(raw: Raw<typeof demoStateSchema>): DemoState {
  return { scenario: raw.scenario, lastResetAt: raw.lastResetAt };
}
