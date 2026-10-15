# Demand Radar — Frontend

Demand Radar captures shopper demand that was never fulfilled (out of stock or
not carried), turns it into reorder recommendations for store managers, and
shows why POS-only forecasting misleads when shelves run dry: **Forecast A**
(POS only) vs. **Forecast B** (POS + unmet demand).

This is the frontend app of the Demand Radar monorepo (`apps/web/`). The backend
(FastAPI + ADK, Gemini, BigQuery/BQML) lives in `services/api/`; the shared
contract is `docs/api-contract.md` at the repo root. The app runs fully in
**mock mode** with no backend.

## Stack

- Next.js (App Router) + TypeScript strict, static export
- Tailwind CSS v4 with design tokens extracted from the UI references
- shadcn-style UI primitives (Radix), `lucide-react`, `recharts`
- `@tanstack/react-query`, `zod`, `vitest`

## Getting started

```bash
cd apps/web                  # or `make web` from the repo root
npm install
cp .env.example .env.local   # mock mode works with the defaults
npm run dev                  # http://localhost:3000
```

### Scripts

| Script | Purpose |
|---|---|
| `npm run dev` | Dev server (proxies `/api/**` to `NEXT_PUBLIC_API_PROXY_TARGET`) |
| `npm run build` | Static export to `out/` |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest unit tests |
| `npm start` | Serve the exported `out/` folder (`npx serve out`) |

## Data modes

`NEXT_PUBLIC_DATA_MODE` selects the data adapter. Components never change.

- **`mock`** (default): fixtures + a simulated realtime emitter. Complete demo
  scenarios run without any backend. Simulated latency 300–1200ms.
- **`live`**: calls `/api/**` with an `X-Sandbox-Id` header, validates every
  response with `zod` and maps it to UI types in one adapter. Realtime uses
  read-only Firestore listeners on the visitor's sandbox (see
  `docs/fe-decisions.md`).

## Environment

See `.env.example`. All variables are `NEXT_PUBLIC_*` (no secrets). Live mode
needs the `NEXT_PUBLIC_FIREBASE_*` web config for realtime; Firestore rules
(`infra/firestore.rules`) allow reads only.

## Demo flow (mock)

1. On `/`, click **Reset demo** to return to "Selasa malam".
2. Open the **Kiosk** and ask for "santan kotak kecil". The assistant replies
   out-of-stock with alternatives and a nearest branch.
3. Within a few seconds the signal appears in the Manager **Live Demand Feed**
   and the KPIs increase.
4. Back on `/`, click **Next morning**: the recommendation becomes Forecast A =
   0, Forecast B = 60, and a critical stockout alert appears in real time.
5. Ask the manager agent "Why should I order 60 boxes of coconut milk?" and open
   the **citations** to jump to the evidence drawer.
6. Open `/manager/gaps` to see "Oat Milk Barista Edition — 142 requests".

## Pages

| Route | Description |
|---|---|
| `/` | Jury page: explanation, scenario buttons, reset demo, links |
| `/kiosk` | Shopper chat (Bahasa Indonesia) with product/alternative/branch cards |
| `/manager` | KPIs, ranked recommendations, live feed, alerts, agent chat |
| `/manager/sku?code=SKU-65ML` | Forecast charts, unmet demand, recommendation, evidence drawer |
| `/manager/gaps` | Products requested but not carried |
| `/about` | Architecture, platform roles, experiment results |

## Project structure

```
src/
├─ app/                 # routes (App Router)
├─ components/          # ui (primitives), layout, kiosk, manager, sku, gaps, about
├─ hooks/               # data + realtime + domain hooks
├─ lib/
│  ├─ api/              # client, contract, schemas, adapters, mock, live, index
│  ├─ realtime/         # mock emitter, live Firestore listeners, index
│  ├─ format.ts         # IDR, Asia/Jakarta dates, relative time
│  ├─ firebase.ts       # lazy Firestore client (live mode)
│  ├─ sandbox.ts        # per-visitor X-Sandbox-Id
│  └─ env.ts
└─ mocks/               # fixtures + in-memory demo state (hero scenario)
```

## Deployment

The build is a static export (`out/`). The repo-root `firebase.json` serves
`apps/web/out` on Firebase Hosting and rewrites `/api/**` to the Cloud Run
service `demand-radar-api`, so the browser talks to the API without CORS.
Deploy with `infra/deploy.sh web` from the repo root.

## Decisions & extensions to the shared contract

See `docs/fe-decisions.md` (stack, static export, SKU route, Firestore
realtime, response shapes to agree, removed internal names, disabled optional features) and
`docs/api-usage.md` (endpoints used and mock behaviours).
