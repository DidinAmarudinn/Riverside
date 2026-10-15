# API usage

The UI talks to the backend only through `src/lib/api/index.ts`, which selects an
adapter based on `NEXT_PUBLIC_DATA_MODE` (`mock` | `live`). Components call
`api.*` and `realtime.*`; they never import adapters directly.

## Endpoints used (live mode)

Contract: repo-root `docs/api-contract.md` §3. Every request carries
`X-Sandbox-Id` (UUID v4 from `src/lib/sandbox.ts`).

| Method & path | Used by | Response |
|---|---|---|
| `GET /api/stores` | Kiosk/Manager store selector | `{ items: [...] }` |
| `GET /api/products?q=` | product search | `{ items: [...] }` |
| `POST /api/kiosk/sessions` | kiosk mount | `{ storeId }` → `{ sessionId }` |
| `POST /api/kiosk/sessions/{id}/messages` | kiosk send | `{ text }` → `{ reply, products, alternatives, nearestBranch? }` |
| `GET /api/manager/{storeId}/overview` | dashboard KPIs (fallback without Firebase) | `{ storeId, kpis, topRisks }` |
| `GET /api/manager/{storeId}/recommendations?risk=` | dashboard table | `{ items: [...] }` |
| `GET /api/manager/{storeId}/sku/{sku}` | SKU detail | SkuDetail: `product`, `kpis`, `sales`, `forecastA`, `forecastB`, `unmetDaily`, `evidence`, `reason` |
| `POST /api/manager/{storeId}/chat` | agent chat | `{ sessionId?, message }` → `{ reply, citations, sessionId }` |
| `GET /api/manager/{storeId}/gaps` | gaps | `{ storeId, items: [GapItem] }` |
| `POST /api/demo/reset` | reset demo | 204 |
| `POST /api/demo/next-morning` | next morning | `{ storeId }` → body ignored |

Field shapes: `docs/api-contract.md` §3.1. The FE merges SKU series by date and
builds the gaps summary itself (`docs/fe-decisions.md` → "Response shapes").

## Firestore listeners (live mode)

Contract §2, read-only, in `src/lib/realtime/live.ts`:

| Path | Used by |
|---|---|
| `sandboxes/{sandboxId}/alerts` (latest 20 by `createdAt`) | alerts panel |
| `sandboxes/{sandboxId}/liveSignals` (latest 20 by `ts`) | live demand feed |
| `metrics/{storeId}` + `sandboxes/{sandboxId}/metrics/{storeId}` | KPI row (baseline + delta) |
| `sandboxes/{sandboxId}` | jury page scenario / last reset |

`GET` requests are retried once. All requests time out after 20s. Errors are
normalized to `{ error: { code, message } }`; HTTP 429 shows "Terlalu cepat,
coba lagi sebentar" and is not auto-retried.

## Mock mode

`src/lib/api/mock.ts` implements the same interface using fixtures in
`src/mocks/`. A shared in-memory store (`src/mocks/state.ts`) drives the
real-time emitter. Simulated latency is 300–1200ms so loading states are
visible.

Demo behaviours reproduced in mock:

- Hero SKU `SKU-0001` (Santan Kotak 65 ml): on-hand 0, 5-day stockout, POS 0.
- Before "Next morning": hero is a low-risk `reorder`. After: `stockout_risk`,
  Forecast A = 0, Forecast B = 60, and a new critical alert appears.
- Asking the kiosk about santan replies with alternatives + nearest branch and
  creates a live signal that increments `lostRevenueToday` and `unmetToday`
  within the same tick (< 5s).
- Reset returns the demo to "Selasa malam".
- Gaps: 8 rows including "Oat Milk Barista Edition — 142 requests".
