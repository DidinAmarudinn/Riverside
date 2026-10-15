import { z } from "zod";

/**
 * Zod schemas for the backend contract (build plan §4.2 & §4.3).
 * Raw payloads are snake_case; adapters.ts maps them to camelCase domain types.
 * Any response that fails validation surfaces as an error state.
 */

export const storeSchema = z.object({
  store_id: z.string(),
  name: z.string(),
  city: z.string(),
  lat: z.number(),
  lng: z.number(),
});

export const productSchema = z.object({
  sku: z.string(),
  name: z.string(),
  brand: z.string().optional().default(""),
  category: z.string().optional().default(""),
  pack_size: z.string().optional(),
  unit: z.string().optional(),
  price_idr: z.number(),
  aisle: z.string().optional(),
  synonyms: z.array(z.string()).optional(),
  is_carried: z.boolean().optional().default(true),
  in_stock: z.boolean().optional(),
  stock_qty: z.number().optional(),
});

const kioskCardSchema = z.object({
  sku: z.string(),
  name: z.string(),
  subtitle: z.string().optional(),
  price_idr: z.number().optional(),
  in_stock: z.boolean(),
  aisle: z.string().optional(),
  stock_qty: z.number().optional(),
});

export const kioskMessageSchema = z.object({
  reply: z.string(),
  products: z.array(kioskCardSchema).default([]),
  alternatives: z.array(kioskCardSchema).default([]),
  nearest_branch: z
    .object({
      store_id: z.string(),
      name: z.string(),
      distance_km: z.number(),
      stock_qty: z.number(),
    })
    .optional(),
});

export const recommendationSchema = z.object({
  store_id: z.string(),
  sku: z.string(),
  name: z.string().optional().default(""),
  category: z.string().optional().default(""),
  on_hand: z.number(),
  forecast_a_7d: z.number(),
  forecast_b_7d: z.number(),
  unmet_7d: z.number().optional().default(0),
  recommended_qty_b: z.number(),
  recommended_qty_a: z.number().optional().default(0),
  risk_type: z.enum(["stockout_risk", "overstock", "reorder", "unmet_spike"]),
  lost_revenue_idr: z.number().optional().default(0),
  reason_text: z.string().optional().default(""),
});

export const metricsSchema = z.object({
  store_id: z.string(),
  lost_revenue_today: z.number(),
  unmet_today: z.number(),
  stockout_skus: z.number(),
  pos_refreshed_at: z.string().optional(),
});

export const overviewSchema = z.object({
  metrics: metricsSchema,
  top_risks: z.array(recommendationSchema).default([]),
});

export const alertSchema = z.object({
  id: z.string(),
  store_id: z.string(),
  sku: z.string().optional(),
  type: z.enum(["stockout_risk", "overstock", "reorder", "unmet_spike"]),
  severity: z.enum(["low", "medium", "high", "critical"]).default("medium"),
  title: z.string(),
  body: z.string().optional().default(""),
  created_at: z.string(),
});

export const liveSignalSchema = z.object({
  id: z.string(),
  store_id: z.string(),
  ts: z.string(),
  requested_text: z.string(),
  sku: z.string().optional(),
  matched_name: z.string().optional(),
  substitute_name: z.string().optional(),
  outcome: z.enum(["purchased", "out_of_stock", "not_carried", "substituted"]),
  source: z.string().optional(),
});

export const citationSchema = z.object({
  label: z.string(),
  sku: z.string().optional(),
  date: z.string().optional(),
  snippet: z.string().optional(),
});

export const managerChatSchema = z.object({
  session_id: z.string(),
  reply: z.string(),
  citations: z.array(citationSchema).default([]),
});

const forecastPointSchema = z.object({
  date: z.string(),
  pos_sales: z.number(),
  forecast_a: z.number(),
  forecast_a_lower: z.number().optional(),
  forecast_a_upper: z.number().optional(),
  forecast_b: z.number(),
  forecast_b_lower: z.number().optional(),
  forecast_b_upper: z.number().optional(),
  is_stockout: z.boolean().default(false),
});

const unmetPointSchema = z.object({
  date: z.string(),
  count: z.number(),
});

const evidenceSchema = z.object({
  id: z.string(),
  ts: z.string(),
  channel: z.string(),
  text: z.string(),
  matched_name: z.string().optional(),
  outcome: z.enum(["purchased", "out_of_stock", "not_carried", "substituted"]),
  confidence: z.number(),
  intent: z.string().optional(),
});

export const skuDetailSchema = z.object({
  sku: z.string(),
  name: z.string(),
  brand: z.string().optional(),
  category: z.string().optional().default(""),
  barcode: z.string().optional(),
  price_idr: z.number(),
  risk_type: z.enum(["stockout_risk", "overstock", "reorder", "unmet_spike"]),
  kpis: z.object({
    on_hand: z.number(),
    on_hand_note: z.string().optional(),
    lost_revenue_idr: z.number(),
    lost_revenue_units: z.number().optional(),
    unmet_requests: z.number(),
    stockout_days: z.number(),
    stockout_since: z.string().optional(),
  }),
  series: z.array(forecastPointSchema).default([]),
  daily_unmet: z.array(unmetPointSchema).default([]),
  recommendation: z.object({
    recommended_qty: z.number(),
    recommended_qty_a: z.number().optional().default(0),
    reason_text: z.string().optional().default(""),
    vendor: z.string().optional(),
    lead_time_days: z.number().optional(),
    urgency: z.enum(["low", "medium", "high"]).optional(),
  }),
  evidence: z.object({
    total: z.number(),
    items: z.array(evidenceSchema).default([]),
  }),
});

export const gapItemSchema = z.object({
  rank: z.number(),
  name: z.string(),
  subtitle: z.string().optional(),
  category: z.string(),
  requests: z.number(),
  trend_7d: z.string(),
  trend_direction: z.enum(["up", "down", "flat"]).default("flat"),
  spark: z.array(z.number()).default([]),
  quote: z.string(),
});

export const gapsSchema = z.object({
  items: z.array(gapItemSchema).default([]),
  summary: z.object({
    total_requests: z.number(),
    lost_revenue_exposure_idr: z.number(),
    categories: z.array(
      z.object({
        name: z.string(),
        count: z.number(),
        percent: z.number(),
      }),
    ),
  }),
});

export const demoStateSchema = z.object({
  scenario: z.string(),
  last_reset_at: z.string(),
});

export const sessionSchema = z.object({
  session_id: z.string(),
});
