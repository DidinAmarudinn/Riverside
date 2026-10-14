# Contract: data, Firestore and API

Source of truth for parallel work (build plan §4). Change it only by PR, and tell the team.
DDL: `sql/01_tables.sql`, views: `sql/02_views.sql`, Firestore rules: `infra/firestore.rules`.

## 1. BigQuery (dataset `demand_radar`, location `us-central1`)

| Table | Main columns | Notes |
|---|---|---|
| `stores` | store_id, name, city, lat, lng | 3 stores |
| `product_master` | sku, name, brand, category, pack_size, unit, price_idr, shelf_life_days, aisle, synonyms (ARRAY&lt;STRING&gt;), is_carried (BOOL) | ~200 SKUs plus ~20 `is_carried = false` items for assortment gaps. Fictional brands only |
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
| `recommendations/{storeId}_{sku}` | baseline summary: on_hand, A, B, recommended, reason, unmet_7d | dashboard table |
| `metrics/{storeId}` | baseline lostRevenueToday, unmetToday, stockoutSkus | KPI row |

**Per-visitor data** (sandbox):

| Collection | Content | Used by |
|---|---|---|
| `sandboxes/{sandboxId}` | scenario, createdAt, lastResetAt | judges page |
| `sandboxes/{sandboxId}/alerts/{id}` | storeId, sku, type (`stockout_risk`, `overstock`, `reorder`, `unmet_spike`), severity, title, body, createdAt | real-time dashboard |
| `sandboxes/{sandboxId}/liveSignals/{id}` | latest signals (requested text, SKU, outcome, ts) | "what shoppers ask for now" feed |
| `sandboxes/{sandboxId}/metrics/{storeId}` | delta from baseline caused by demo activity | KPI row (baseline + delta) |
| `sandboxes/{sandboxId}/recommendations/{storeId}_{sku}` | "next morning" results that override the baseline | dashboard table |
| `sandboxes/{sandboxId}/sessions/{id}/messages/{id}` | kiosk and manager chat history, including agent session state | backend only |

Rules: public **read** for base data and `sandboxes/{sandboxId}/**` except `sessions`. `sandboxId` is a random UUID, so it
cannot be guessed. All client **writes are denied**; the backend writes with the Admin SDK.

## 3. API (FastAPI behind `/api`)

Every kiosk, manager and demo endpoint reads the `X-Sandbox-Id` header (UUID v4, validated by the backend). A sandbox is
created on first use. The browser creates the id on first visit, keeps it in localStorage and sends it on every request.

| Method & path | Request | Response |
|---|---|---|
| `GET /api/healthz` | | `{ok}` |
| `GET /api/stores` | | list of stores |
| `GET /api/products?q=` | | product search results |
| `POST /api/kiosk/sessions` | `{storeId}` | `{sessionId}` |
| `POST /api/kiosk/sessions/{id}/messages` | `{text}` (optional: `imageBase64`, `audioBase64`) | `{reply, products: [{sku, name, inStock, aisle}], alternatives: [], nearestBranch?}` |
| `GET /api/manager/{storeId}/overview` | | KPIs + top risks |
| `GET /api/manager/{storeId}/recommendations` | `?risk=` | recommendation list |
| `GET /api/manager/{storeId}/sku/{sku}` | | forecast A/B series + sales, daily unmet, evidence (quotes) |
| `POST /api/manager/{storeId}/chat` | `{sessionId?, message}` | `{reply, citations: [], sessionId}` |
| `GET /api/manager/{storeId}/gaps` | | products asked for but not carried, by category |
| `GET /api/manager/{storeId}/trends` (optional) | | rising new demand |
| `POST /api/manager/recommendations/{id}/approve` (optional) | | draft PO |
| `POST /api/demo/reset` | | deletes this visitor's sandbox content; base data untouched |
| `POST /api/demo/next-morning` | `{storeId}` | recomputes the hero scenario's recommendations with the reorder formula (build plan §7); results go to the sandbox |
| `POST /pubsub/extract` | Pub/Sub push envelope (valid OIDC token required) | 204; 401 if the token is invalid |

Uniform error format: `{"error": {"code", "message"}}`. Every response < 10 s; anything slower shows a loading state.

Firebase Hosting rewrites **only** `/api/**` to Cloud Run. Pub/Sub pushes straight to the Cloud Run URL
(`/pubsub/extract`), never through Hosting.
