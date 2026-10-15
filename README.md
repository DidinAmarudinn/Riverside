# Demand Radar — Frontend

Demand Radar captures shopper demand that was never fulfilled (out of stock or
not carried), turns it into reorder recommendations for store managers, and
shows why POS-only forecasting misleads when shelves run dry: **Forecast A**
(POS only) vs. **Forecast B** (POS + unmet demand).

This repository is the **frontend only**. The backend (FastAPI + ADK, Gemini,
BigQuery/BQML) is built by other team members. The app runs fully in **mock
mode** with no backend.

## Stack

- Next.js (App Router) + TypeScript strict, static export
- Tailwind CSS v4 with design tokens extracted from the UI references
- shadcn-style UI primitives (Radix), `lucide-react`, `recharts`
- `@tanstack/react-query`, `zod`, `vitest`

## Getting started

```bash
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
- **`live`**: calls `/api/**`, validates every response with `zod`, and maps
  `snake_case` → `camelCase` in one adapter. Realtime uses HTTP polling (there is
  no Firestore in this build — see `docs/fe-decisions.md`).

## Environment

See `.env.example`. All variables are `NEXT_PUBLIC_*` (no secrets). There is no
Firebase configuration in this build.

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
│  ├─ realtime/         # mock emitter, live polling, index
│  ├─ format.ts         # IDR, Asia/Jakarta dates, relative time
│  └─ env.ts
└─ mocks/               # fixtures + in-memory demo state (hero scenario)
```

## Deployment

The build is a static export (`out/`). Deploy it to any static host (e.g.
Firebase Hosting) and rewrite `/api/**` to the Cloud Run service so the browser
talks to the API without CORS. Example `firebase.json`:

```json
{
  "hosting": {
    "public": "out",
    "rewrites": [
      { "source": "/api/**", "destination": "https://<cloud-run-service>" }
    ]
  }
}
```

## Decisions & extensions to the shared contract

See `docs/fe-decisions.md` (stack, static export, SKU route, no-Firebase
realtime, removed internal names, disabled optional features) and
`docs/api-usage.md` (endpoints used and mock behaviours).
