import type { z } from "zod";
import type {
  AlertItem,
  DemoState,
  GapsResponse,
  KioskMessageResponse,
  LiveSignal,
  ManagerChatResponse,
  Metrics,
  Outcome,
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
  return {
    id: raw.store_id,
    name: raw.name,
    city: raw.city,
    lat: raw.lat,
    lng: raw.lng,
  };
}

export function adaptProduct(raw: Raw<typeof productSchema>): Product {
  return {
    sku: raw.sku,
    name: raw.name,
    brand: raw.brand,
    category: raw.category,
    packSize: raw.pack_size,
    unit: raw.unit,
    priceIdr: raw.price_idr,
    aisle: raw.aisle,
    synonyms: raw.synonyms,
    isCarried: raw.is_carried,
    inStock: raw.in_stock,
    stockQty: raw.stock_qty,
  };
}

export function adaptKioskMessage(
  raw: Raw<typeof kioskMessageSchema>,
): KioskMessageResponse {
  return {
    reply: raw.reply,
    products: raw.products.map((p) => ({
      sku: p.sku,
      name: p.name,
      subtitle: p.subtitle,
      priceIdr: p.price_idr,
      inStock: p.in_stock,
      aisle: p.aisle,
      stockQty: p.stock_qty,
    })),
    alternatives: raw.alternatives.map((p) => ({
      sku: p.sku,
      name: p.name,
      subtitle: p.subtitle,
      priceIdr: p.price_idr,
      inStock: p.in_stock,
      aisle: p.aisle,
      stockQty: p.stock_qty,
    })),
    nearestBranch: raw.nearest_branch
      ? {
          storeId: raw.nearest_branch.store_id,
          name: raw.nearest_branch.name,
          distanceKm: raw.nearest_branch.distance_km,
          stockQty: raw.nearest_branch.stock_qty,
        }
      : undefined,
  };
}

export function adaptRecommendation(
  raw: Raw<typeof recommendationSchema>,
): Recommendation {
  return {
    storeId: raw.store_id,
    sku: raw.sku,
    name: raw.name,
    category: raw.category,
    onHand: raw.on_hand,
    forecastA: raw.forecast_a_7d,
    forecastB: raw.forecast_b_7d,
    unmet7d: raw.unmet_7d,
    recommendedQty: raw.recommended_qty_b,
    recommendedQtyA: raw.recommended_qty_a,
    riskType: raw.risk_type,
    lostRevenueIdr: raw.lost_revenue_idr,
    reasonText: raw.reason_text,
  };
}

export function adaptMetrics(raw: Raw<typeof metricsSchema>): Metrics {
  return {
    storeId: raw.store_id,
    lostRevenueToday: raw.lost_revenue_today,
    unmetToday: raw.unmet_today,
    stockoutSkus: raw.stockout_skus,
    posRefreshedAt: raw.pos_refreshed_at,
  };
}

export function adaptOverview(raw: Raw<typeof overviewSchema>): Overview {
  return {
    metrics: adaptMetrics(raw.metrics),
    topRisks: raw.top_risks.map(adaptRecommendation),
  };
}

export function adaptAlert(raw: Raw<typeof alertSchema>): AlertItem {
  return {
    id: raw.id,
    storeId: raw.store_id,
    sku: raw.sku,
    type: raw.type,
    severity: raw.severity,
    title: raw.title,
    body: raw.body,
    createdAt: raw.created_at,
  };
}

export function adaptSignal(raw: Raw<typeof liveSignalSchema>): LiveSignal {
  return {
    id: raw.id,
    storeId: raw.store_id,
    ts: raw.ts,
    requestedText: raw.requested_text,
    sku: raw.sku,
    matchedName: raw.matched_name,
    substituteName: raw.substitute_name,
    outcome: raw.outcome as Outcome,
    source: raw.source,
  };
}

export function adaptManagerChat(
  raw: Raw<typeof managerChatSchema>,
): ManagerChatResponse {
  return {
    sessionId: raw.session_id,
    reply: raw.reply,
    citations: raw.citations,
  };
}

export function adaptSkuDetail(raw: Raw<typeof skuDetailSchema>): SkuDetail {
  return {
    sku: raw.sku,
    name: raw.name,
    brand: raw.brand,
    category: raw.category,
    barcode: raw.barcode,
    priceIdr: raw.price_idr,
    riskType: raw.risk_type,
    kpis: {
      onHand: raw.kpis.on_hand,
      onHandNote: raw.kpis.on_hand_note,
      lostRevenueIdr: raw.kpis.lost_revenue_idr,
      lostRevenueUnits: raw.kpis.lost_revenue_units,
      unmetRequests: raw.kpis.unmet_requests,
      stockoutDays: raw.kpis.stockout_days,
      stockoutSince: raw.kpis.stockout_since,
    },
    series: raw.series.map((p) => ({
      date: p.date,
      posSales: p.pos_sales,
      forecastA: p.forecast_a,
      forecastALower: p.forecast_a_lower,
      forecastAUpper: p.forecast_a_upper,
      forecastB: p.forecast_b,
      forecastBLower: p.forecast_b_lower,
      forecastBUpper: p.forecast_b_upper,
      isStockout: p.is_stockout,
    })),
    dailyUnmet: raw.daily_unmet,
    recommendation: {
      recommendedQty: raw.recommendation.recommended_qty,
      recommendedQtyA: raw.recommendation.recommended_qty_a,
      reasonText: raw.recommendation.reason_text,
      vendor: raw.recommendation.vendor,
      leadTimeDays: raw.recommendation.lead_time_days,
      urgency: raw.recommendation.urgency,
    },
    evidence: {
      total: raw.evidence.total,
      items: raw.evidence.items.map((e) => ({
        id: e.id,
        ts: e.ts,
        channel: e.channel,
        text: e.text,
        matchedName: e.matched_name,
        outcome: e.outcome as Outcome,
        confidence: e.confidence,
        intent: e.intent,
      })),
    },
  };
}

export function adaptGaps(raw: Raw<typeof gapsSchema>): GapsResponse {
  return {
    items: raw.items.map((g) => ({
      rank: g.rank,
      name: g.name,
      subtitle: g.subtitle,
      category: g.category,
      requests: g.requests,
      trend7d: g.trend_7d,
      trendDirection: g.trend_direction,
      spark: g.spark,
      quote: g.quote,
    })),
    summary: {
      totalRequests: raw.summary.total_requests,
      lostRevenueExposureIdr: raw.summary.lost_revenue_exposure_idr,
      categories: raw.summary.categories,
    },
  };
}

export function adaptDemoState(raw: Raw<typeof demoStateSchema>): DemoState {
  return { scenario: raw.scenario, lastResetAt: raw.last_reset_at };
}
