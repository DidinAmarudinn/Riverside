# Contract: data, Firestore and API

Source of truth for parallel work (build plan §4). Change it only by PR, and tell the team.
DDL: `sql/01_tables.sql`, views: `sql/02_views.sql`, Firestore rules: `infra/firestore.rules`.

## 1. BigQuery (dataset `demand_radar`, location `us-central1`)

| Table | Main columns | Notes |
|---|---|---|
| `stores` | store_id, name, city, lat, lng | 3 stores |
| `product_master` | sku, name, brand, category, pack_size, unit, price_idr, shelf_life_days, aisle, synonyms (ARRAY&lt;STRING&gt;), is_carried (BOOL) | ~200 SKUs plus ~20 `is_carried = false` items for assortment gaps. Familiar Indonesian grocery brand names for realism; all stock, sales, prices and conversations are simulated |
| `calendar_context` | date, is_payday_window, is_holiday, holiday_name, is_ramadan, is_lebaran_window, weather | Forecast input and context for agent explanations |
| `true_demand` | date, store_id, sku, demand_qty | Simulation ground truth. **Never readable by agents** |
| `stock_events` | date, store_id, sku, opening_stock, received_qty, closing_stock, is_stockout | |
| `pos_sales` | date, store_id, sku, qty_sold, revenue_idr | `qty_sold = min(demand, stock)` |
| `conversations` | conversation_id, store_id, ts, channel, transcript, gt_sku, gt_outcome | `gt_*` only for scoring extraction accuracy; never in any view |
| `demand_signals` | signal_id, conversation_id, sandbox_id (nullable), store_id, ts, date, requested_text, sku (nullable), normalized_name, category, outcome, substitute_sku, qty, confidence, model_version | Extractor output. `sandbox_id` is null for historical data, set for live demo signals |
| `forecasts` | run_date, store_id, sku, model (`A`/`B`), forecast_date, forecast_qty, lower, upper | |
| `recommendations` | run_date, store_id, sku, on_hand, forecast_a_7d, forecast_b_7d, unmet_7d, recommended_qty_a, recommended_qty_b, risk_type, lost_revenue_idr, reason_text | One row per SKU per store per run |

`outcome` values: `purchased`, `out_of_stock`, `not_carried`, `substituted`, plus `low_confidence` for signals under the
0.7 confidence threshold (stored, never counted in forecast B).

**Agent views (read-only):** `v_unmet_daily`, `v_sku_summary`, `v_assortment_gaps`, `v_evidence` (conversation quotes per SKU),
`v_lost_revenue_today`. Views never expose `true_demand` or `gt_sku` / `gt_outcome`: they are the simulation's answer key.
Views hold base data only; agent tools merge them with the visitor's sandbox data from Firestore.

## 2. Firestore (clients read only)

**Base data** (shared, written by a sync script from BigQuery):

| Collection | Content | Used by |
|---|---|---|
| `recommendations/{storeId}_{sku}` | a **Recommendation** (§3.1) | dashboard table |
| `metrics/{storeId}` | **Metrics** (§3.1): lostRevenueToday, unmetToday, stockoutSkus, posRefreshedAt? | KPI row |

**Per-visitor data** (sandbox):

| Collection | Content | Used by |
|---|---|---|
| `sandboxes/{sandboxId}` | scenario, createdAt, lastResetAt | judges page |
| `sandboxes/{sandboxId}/alerts/{id}` | storeId, sku?, type (`stockout_risk`, `overstock`, `reorder`, `unmet_spike`), severity (`low`, `medium`, `high`, `critical`), title, body, createdAt (Timestamp) | real-time dashboard |
| `sandboxes/{sandboxId}/liveSignals/{id}` | storeId, ts (Timestamp), requestedText, sku?, matchedName? (product name of `sku`), outcome, substituteName?, source? (e.g. `Kiosk`) | "what shoppers ask for now" feed |
| `sandboxes/{sandboxId}/metrics/{storeId}` | **Metrics** delta from baseline caused by demo activity (same fields, added to the baseline) | KPI row (baseline + delta) |
| `sandboxes/{sandboxId}/recommendations/{storeId}_{sku}` | a **Recommendation**: "next morning" result that overrides the baseline | dashboard table |
| `sandboxes/{sandboxId}/sessions/{id}/messages/{id}` | kiosk and manager chat history, including agent session state | backend only |

The client reads the latest 20 alerts (by `createdAt`) and liveSignals (by `ts`) and filters by `storeId` itself, so no
composite index is needed. `low_confidence` signals may be written but are never shown. A kiosk chat writes **one liveSignal per product the
shopper asks about** (id `sig-{conversationId}`, then `sig-{conversationId}-1`, `-2`…): a turn in which the agent searches
for a product starts a new one, follow-ups without a search ("boleh", "di rak mana?") update the current one.

Rules: public **read** for base data and `sandboxes/{sandboxId}/**` except `sessions`. `sandboxId` is a random UUID, so it
cannot be guessed. All client **writes are denied**; the backend writes with the Admin SDK.

## 3. API (FastAPI behind `/api`)

**Naming:** every JSON body and Firestore document is camelCase. Fields that come from a §1 column use the camelCased
column name (`price_idr` → `priceIdr`, `forecast_a_7d` → `forecastA7d`). IDs are the data's own: stores `S01`–`S03`,
SKUs `SKU-0001`… (the hero is `S01` / `SKU-0001`). Lists are wrapped as `{items: [...]}`.

Every kiosk, manager and demo endpoint reads the `X-Sandbox-Id` header (UUID v4, validated by the backend). A sandbox is
created on first use. The browser creates the id on first visit, keeps it in localStorage and sends it on every request.

| Method & path | Request | Response |
|---|---|---|
| `GET /api/healthz` | | `{ok}` |
| `GET /api/stores` | | `{items: [Store]}` |
| `GET /api/products?q=` | | `{items: [Product]}` |
| `POST /api/kiosk/sessions` | `{storeId}` | `{sessionId}` |
| `POST /api/kiosk/sessions/{id}/messages` | `{text}` (optional: `imageBase64`, `audioBase64`) | `{reply, products: [KioskProduct], alternatives: [KioskProduct], nearestBranch: Branch \| null}` |
| `GET /api/manager/{storeId}/overview` | | `{storeId, kpis: Metrics, topRisks: [Recommendation]}` |
| `GET /api/manager/{storeId}/recommendations` | `?risk=` | `{storeId, items: [Recommendation]}`, most at-risk first |
| `GET /api/manager/{storeId}/sku/{sku}` | | **SkuDetail** (§3.1) |
| `POST /api/manager/{storeId}/chat` | `{sessionId?, message, sku?}` (`sku`: the product on screen, if any) | `{reply, citations: [Citation], sessionId}` |
| `GET /api/manager/{storeId}/gaps` | | `{storeId, items: [GapItem]}`, most requested first |
| `GET /api/manager/{storeId}/trends` (optional) | | rising new demand |
| `POST /api/manager/recommendations/{id}/approve` (optional) | | draft PO |
| `POST /api/demo/reset` | | deletes this visitor's sandbox content; base data untouched |
| `POST /api/demo/next-morning` | `{storeId}` → `{storeId, updated}` | placeholder, returns `updated: 0`; not used by the web app. The hero recommendations (A 10, B 64) are computed by the forecast pipeline and exist from the start, so the demo has no "next morning" step |
| `POST /pubsub/extract` | Pub/Sub push envelope (valid OIDC token required) | 204; 401 if the token is invalid |

Uniform error format: `{"error": {"code", "message"}}`. Every response < 10 s; anything slower shows a loading state.

Firebase Hosting rewrites **only** `/api/**` to Cloud Run. Pub/Sub pushes straight to the Cloud Run URL
(`/pubsub/extract`), never through Hosting.

### 3.1 Response objects

`?` marks an optional field (omit it or send `null`). Dates are `YYYY-MM-DD`, timestamps ISO 8601 (Timestamp in
Firestore). Amounts in IDR are integers.

| Object | Fields |
|---|---|
| Store | storeId, name, city, lat, lng |
| Product | sku, name, brand, category, packSize, unit?, priceIdr, aisle, isCarried, inStock? |
| KioskProduct | sku, name, inStock, aisle, priceIdr?, stockQty? |
| Branch | storeId, name, distanceKm, stockQty |
| Metrics | lostRevenueToday, unmetToday, stockoutSkus, posRefreshedAt? |
| Recommendation | storeId, sku, name, category, onHand, forecastA7d, forecastB7d, unmet7d, recommendedQtyA, recommendedQtyB, riskType, lostRevenueIdr, reasonText |
| SkuDetail | storeId, sku, product: {name, brand, category, packSize, priceIdr, aisle}, riskType, kpis: {onHand, lostRevenueIdr (last 7 days), lostRevenueUnits (lostRevenueIdr / price), unmetRequests (over the running stockout, else last 7 days), unmetWindowDays, unmetRequests7d, stockoutDays, stockoutSince?}, sales: [{date, qty, isStockout}], forecastA: [{date, qty, lower?, upper?}], forecastB: [same], unmetDaily: [{date, count}], evidence: {total, items: [Evidence]}, reason: {recommendedQtyA, recommendedQtyB, reasonText, leadTimeDays?} |
| Evidence | id (conversation_id), ts, channel, quote (what the shopper said), outcome, confidence |
| Citation | label, sku? (links to that SKU's evidence drawer), date?, quote? |
| GapItem | name (normalized_name), category, requests, firstSeen, lastSeen, daily: [counts for the last 14 days, oldest first], trend7dPct (last 7 days vs the 7 before, %), quote? (one shopper quote), estRevenueIdr? (requests × typical category price) |

Notes:
- **SkuDetail** keeps sales and the two forecasts as separate series on their own dates (A and B may cover history and
  the horizon); the UI merges them by date. `kpis.lostRevenueUnits` is the estimated unmet units behind
  `lostRevenueIdr`. Evidence never includes `gt_*` columns, `low_confidence` signals or `true_demand`.
- **GapItem**: the UI ranks items and computes the per-category summary (count, share) and total exposure itself.
- `riskType`, `outcome` and alert `type` use the enums from §1–2.

