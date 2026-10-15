# Frontend decisions

Running log of decisions and deviations taken while building the Demand Radar
frontend. Owner: frontend. Newest decisions added at the bottom of each section.

## Scope & stack

- **Next.js app in `apps/web/`** of the monorepo (build plan §3). It replaced
  the earlier Vite scaffold. Build output is `out/`, served by the repo-root
  `firebase.json`.
- **Next.js App Router, TypeScript strict, Tailwind CSS v4** (design tokens in
  `src/app/globals.css` via `@theme`), shadcn-style primitives built on Radix,
  `lucide-react`, `recharts`, `@tanstack/react-query`, `zod`, `vitest`.
- **Static export** (`output: "export"`, `images.unoptimized`, `trailingSlash`)
  is the default target. No Server Actions, Route Handlers, Middleware or ISR.
  All data is fetched on the client to relative `/api/...` paths.
- `next dev` proxies `/api/**` to `NEXT_PUBLIC_API_PROXY_TARGET` via `rewrites`.
  Rewrites are intentionally disabled in production (they are a no-op with a
  static export); this causes a harmless build warning.

## Routing

- **SKU detail uses a query param** `/manager/sku?code=SKU-0001` instead of a
  dynamic `[sku]` segment, so the data-team can add SKUs without a rebuild and
  static export works for every SKU. Deep links from chat citations use
  `/manager/sku?code=...&evidence=open`.

## Data layer (follows docs/api-contract.md)

- **Contract first.** The FE adapts to the repo-root `docs/api-contract.md`;
  contract changes go through a PR. An earlier draft of this app replaced
  Firestore with polling against invented endpoints (`/api/demo/state`,
  `/api/manager/{storeId}/alerts`, `/live-signals`); that was reverted.
- **Sandbox.** `src/lib/sandbox.ts` creates a UUID v4 on first visit, keeps it in
  localStorage and `client.ts` sends it as `X-Sandbox-Id` on every request (the
  API returns 400 without it). Firestore listeners use the same id.
- **Realtime** sits behind `RealtimeClient` (`src/lib/realtime/index.ts`):
  - `mock` mode: an in-memory emitter (`src/mocks/state.ts`) that fires on kiosk
    signals, "next morning" and reset.
  - `live` mode: read-only Firestore `onSnapshot` (`src/lib/realtime/live.ts`):
    `sandboxes/{id}/alerts`, `sandboxes/{id}/liveSignals`, `metrics/{storeId}`
    + `sandboxes/{id}/metrics/{storeId}` (baseline + delta), and
    `sandboxes/{id}` for the demo state. Feeds are ordered by
    `createdAt` / `ts` and filtered by store client-side (no composite index).
    Without `NEXT_PUBLIC_FIREBASE_*`, only the KPI row loads, once, from
    `/overview`.
- **Payloads are camelCase** (as in contract §2–3: `sessionId`, `inStock`,
  `nearestBranch`, `lostRevenueToday`); field names from BigQuery are
  camelCased (`price_idr` → `priceIdr`, `forecast_a_7d` → `forecastA7d`). Lists
  are `{ items: [...] }`. All responses are validated with `zod`
  (`src/lib/api/schemas.ts`) and mapped to UI types in `adapters.ts`. The UI
  never reads `true_demand` or `gt_*` fields; `low_confidence` signals are
  dropped from the live feed.
- `POST /api/demo/reset` returns 204 and `POST /api/demo/next-morning` returns
  `{ storeId, updated }`; the UI ignores both bodies and picks up the new state
  from Firestore.
- `NEXT_PUBLIC_DATA_MODE` selects the adapter (`mock` default).

## Response shapes (contract §3.1, decided 15 Oct)

The field-level shapes now live in the repo-root `docs/api-contract.md` §3.1;
backend stubs in `services/api/app/main.py` return them. What the FE does on
top of them (`src/lib/api/adapters.ts`):

- **SkuDetail**: the API sends `sales`, `forecastA`, `forecastB` as separate
  series; the FE merges them by date (a missing value is `null`, drawn as a gap).
  `urgency` is derived from `riskType`. Barcode, vendor and evidence intent are
  not in the contract and are only shown in mock mode.
- **GapItem**: the FE ranks items by `requests`, formats `trend7dPct`, and builds
  the per-category summary and total exposure (`estRevenueIdr`).
- **Citation**: `{ label, sku?, date?, quote? }`; a citation with `sku` opens that
  SKU's evidence drawer.
- **IDs** follow the data (`S01`–`S03`, hero `SKU-0001`); mocks use the same IDs.

## Design fidelity

- **Icons**: the Stitch screens use Material Symbols; the stack mandates
  `lucide-react`, so icons are mapped to the closest Lucide equivalent (e.g.
  `radar` → `Radar`, `smart_toy` → `Bot`). Layout/spacing/hierarchy follow the
  screens; only the icon set differs.
- **Charts**: the SKU screens ship hand-drawn SVG; they are reproduced with
  `recharts` (POS bars `#dce9ff`, Forecast A dashed `#6e7977`, Forecast B teal
  `#0f766e`, teal band + red stockout shading).
- **Palettes**: the Kiosk and Manager surfaces use different but related teal
  shades (`#0f766e` vs `#005c55`); both are preserved per the screens.
- **Time format**: `Intl` with locale `id-ID` renders `14.22`; the UI forces a
  colon (`14:22`) to match the screens.
- **Removed content**: the screens contained an internal company name in the
  footer (`PT Telemetri Retail Indonesia`) and the label `Demand Radar
  Synthetics`; both were removed/replaced (`Demand Radar Insights`, generic
  footer). No internal product names exist in code, UI, mocks or commits.

## Feature flags / optional work

- Camera (Foto) and microphone (Suara) kiosk buttons render but are disabled
  behind `NEXT_PUBLIC_FEATURE_MULTIMODAL=false` with a "Segera hadir" tooltip.
- "Approve selected POs", "Export telemetry", "Create PO", branch routing and
  "Generate pitch deck" buttons render disabled (optional features, PRD §2).
- `public/results.json` holds placeholder experiment figures; the data team can
  replace the file without a rebuild.

## Known deviations / follow-ups

- The jury page has no Stitch reference; it reuses the Manager visual language.
- `/about` describes the platform roles (Cloud Run, Gemini, BigQuery/BQML,
  Firebase Hosting + Firestore).
- Mock serves the same dataset for every store (Toko 2/3 relabel), sufficient
  for the demo; live mode uses `storeId` from the API.
