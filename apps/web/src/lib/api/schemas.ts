import { z } from "zod";

/**
 * Zod schemas for the backend contract (docs/api-contract.md).
 * API and Firestore payloads are camelCase (column names from §1 camelCased:
 * `price_idr` → `priceIdr`, `forecast_a_7d` → `forecastA7d`). adapters.ts maps
 * them to the UI domain types. Any response that fails validation surfaces as
 * an error state.
 */

const riskType = z.enum(["stockout_risk", "overstock", "reorder", "unmet_spike"]);
const outcome = z.enum(["purchased", "out_of_stock", "not_carried", "substituted"]);

/** Firestore Timestamp (has toDate) or ISO string → ISO string. */
const timestamp = z.preprocess(
  (v) =>
    v && typeof v === "object" && "toDate" in v
      ? (v as { toDate: () => Date }).toDate().toISOString()
      : v,
  z.string(),
);

export const storeSchema = z.object({
  storeId: z.string(),
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
  packSize: z.string().optional(),
  unit: z.string().optional(),
  priceIdr: z.number(),
  aisle: z.string().optional(),
  synonyms: z.array(z.string()).optional(),
  isCarried: z.boolean().optional().default(true),
  inStock: z.boolean().optional(),
  stockQty: z.number().optional(),
});

const kioskCardSchema = z.object({
  sku: z.string(),
  name: z.string(),
  subtitle: z.string().optional(),
  priceIdr: z.number().optional(),
  inStock: z.boolean(),
  aisle: z.string().optional(),
  stockQty: z.number().optional(),
});

export const kioskMessageSchema = z.object({
  reply: z.string(),
  products: z.array(kioskCardSchema).default([]),
  alternatives: z.array(kioskCardSchema).default([]),
  nearestBranch: z
    .object({
      storeId: z.string(),
      name: z.string(),
      distanceKm: z.number(),
      stockQty: z.number(),
    })
    .nullish(),
});

export const recommendationSchema = z.object({
  storeId: z.string(),
  sku: z.string(),
  name: z.string().optional().default(""),
  category: z.string().optional().default(""),
  onHand: z.number(),
  forecastA7d: z.number(),
  forecastB7d: z.number(),
  unmet7d: z.number().optional().default(0),
  recommendedQtyB: z.number(),
  recommendedQtyA: z.number().optional().default(0),
  riskType,
  lostRevenueIdr: z.number().optional().default(0),
  reasonText: z.string().optional().default(""),
});

/** KPI row: `metrics/{storeId}` and `sandboxes/{id}/metrics/{storeId}` (delta). */
export const metricsSchema = z.object({
  lostRevenueToday: z.number().default(0),
  unmetToday: z.number().default(0),
  stockoutSkus: z.number().default(0),
  posRefreshedAt: timestamp.optional(),
});

export const overviewSchema = z.object({
  storeId: z.string(),
  kpis: metricsSchema,
  topRisks: z.array(recommendationSchema).default([]),
});

/** `sandboxes/{id}/alerts/{id}` (Firestore). */
export const alertSchema = z.object({
  id: z.string(),
  storeId: z.string(),
  sku: z.string().optional(),
  type: riskType,
  severity: z.enum(["low", "medium", "high", "critical"]).default("medium"),
  title: z.string(),
  body: z.string().optional().default(""),
  createdAt: timestamp,
});

/** `sandboxes/{id}/liveSignals/{id}` (Firestore). */
export const liveSignalSchema = z.object({
  id: z.string(),
  storeId: z.string().optional(),
  ts: timestamp,
  requestedText: z.string(),
  sku: z.string().nullish(),
  matchedName: z.string().optional(),
  substituteName: z.string().optional(),
  // low_confidence signals are stored but never shown as demand (§1).
  outcome: z.union([outcome, z.literal("low_confidence")]),
  source: z.string().optional(),
});

/** `sandboxes/{id}` (Firestore). */
export const demoStateSchema = z.object({
  scenario: z.string().default("Selasa malam"),
  lastResetAt: timestamp.optional(),
  createdAt: timestamp.optional(),
});

export const citationSchema = z.object({
  label: z.string(),
  sku: z.string().nullish(),
  date: z.string().nullish(),
  quote: z.string().nullish(),
});

export const managerChatSchema = z.object({
  sessionId: z.string(),
  reply: z.string(),
  citations: z.array(citationSchema).default([]),
});

const seriesPointSchema = z.object({
  date: z.string(),
  qty: z.number(),
  lower: z.number().nullish(),
  upper: z.number().nullish(),
});

const evidenceSchema = z.object({
  id: z.string(),
  ts: z.string(),
  channel: z.string(),
  quote: z.string(),
  outcome,
  confidence: z.number(),
});

/** SkuDetail (contract §3.1). Series stay separate; adapters merge by date. */
export const skuDetailSchema = z.object({
  storeId: z.string(),
  sku: z.string(),
  product: z.object({
    name: z.string(),
    brand: z.string().optional(),
    category: z.string().optional().default(""),
    packSize: z.string().optional(),
    priceIdr: z.number(),
    aisle: z.string().optional(),
  }),
  riskType,
  kpis: z.object({
    onHand: z.number(),
    lostRevenueIdr: z.number(),
    lostRevenueUnits: z.number().optional(),
    unmetRequests: z.number(),
    stockoutDays: z.number(),
    stockoutSince: z.string().nullish(),
  }),
  sales: z
    .array(
      z.object({
        date: z.string(),
        qty: z.number(),
        isStockout: z.boolean().default(false),
      }),
    )
    .default([]),
  forecastA: z.array(seriesPointSchema).default([]),
  forecastB: z.array(seriesPointSchema).default([]),
  unmetDaily: z
    .array(z.object({ date: z.string(), count: z.number() }))
    .default([]),
  evidence: z.object({
    total: z.number(),
    items: z.array(evidenceSchema).default([]),
  }),
  reason: z.object({
    recommendedQtyA: z.number().default(0),
    recommendedQtyB: z.number(),
    reasonText: z.string().default(""),
    leadTimeDays: z.number().nullish(),
  }),
});

/** GapItem (contract §3.1). The UI ranks items and builds the summary. */
export const gapItemSchema = z.object({
  name: z.string(),
  category: z.string(),
  requests: z.number(),
  firstSeen: z.string().optional(),
  lastSeen: z.string().optional(),
  daily: z.array(z.number()).default([]),
  trend7dPct: z.number().default(0),
  quote: z.string().nullish(),
  estRevenueIdr: z.number().nullish(),
});

export const gapsSchema = z.object({
  storeId: z.string(),
  items: z.array(gapItemSchema).default([]),
});

export const sessionSchema = z.object({
  sessionId: z.string(),
});
