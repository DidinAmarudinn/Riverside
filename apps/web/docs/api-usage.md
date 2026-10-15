# API usage

The UI talks to the backend only through `src/lib/api/index.ts`, which selects an
adapter based on `NEXT_PUBLIC_DATA_MODE` (`mock` | `live`). Components call
`api.*` and `realtime.*`; they never import adapters directly.

## Endpoints used (live mode)

| Method & path | Used by | Notes |
|---|---|---|
| `GET /api/stores` | Kiosk/Manager store selector | `{ stores: [...] }` |
| `GET /api/products?q=` | product search | `{ products: [...] }` |
| `POST /api/kiosk/sessions` | kiosk mount | `{ storeId }` → `{ session_id }` |
| `POST /api/kiosk/sessions/{id}/messages` | kiosk send | `{ text }` → products, alternatives, branch |
| `GET /api/manager/{storeId}/overview` | dashboard KPIs | `{ metrics, top_risks }` |
| `GET /api/manager/{storeId}/recommendations?risk=` | dashboard table | `{ recommendations }` |
| `GET /api/manager/{storeId}/sku/{sku}` | SKU detail | series, daily unmet, evidence |
| `POST /api/manager/{storeId}/chat` | agent chat | `{ sessionId?, message }` → reply + citations |
| `GET /api/manager/{storeId}/gaps` | gaps | items + summary |
| `GET /api/demo/state` | jury status chip | `{ scenario, last_reset_at }` |
| `POST /api/demo/reset` | reset demo | returns new demo state |
| `POST /api/demo/next-morning` | next morning | `{ storeId }` → new demo state |
| `GET /api/manager/{storeId}/alerts` | realtime alerts | polled every 5s (assumed) |
| `GET /api/manager/{storeId}/live-signals` | realtime feed | polled every 5s (assumed) |

`GET` requests are retried once. All requests time out after 20s. Errors are
normalized to `{ error: { code, message } }`; HTTP 429 shows "Terlalu cepat,
coba lagi sebentar" and is not auto-retried.

## Mock mode

`src/lib/api/mock.ts` implements the same interface using fixtures in
`src/mocks/`. A shared in-memory store (`src/mocks/state.ts`) drives the
real-time emitter. Simulated latency is 300–1200ms so loading states are
visible.

Demo behaviours reproduced in mock:

- Hero SKU `SKU-65ML` (Santan Kotak 65 ml): on-hand 0, 5-day stockout, POS 0.
- Before "Next morning": hero is a low-risk `reorder`. After: `stockout_risk`,
  Forecast A = 0, Forecast B = 60, and a new critical alert appears.
- Asking the kiosk about santan replies with alternatives + nearest branch and
  creates a live signal that increments `lostRevenueToday` and `unmetToday`
  within the same tick (< 5s).
- Reset returns the demo to "Selasa malam".
- Gaps: 8 rows including "Oat Milk Barista Edition — 142 requests".
