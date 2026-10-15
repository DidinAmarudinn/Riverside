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

- **SKU detail uses a query param** `/manager/sku?code=SKU-65ML` instead of a
  dynamic `[sku]` segment, so the data-team can add SKUs without a rebuild and
  static export works for every SKU. Deep links from chat citations use
  `/manager/sku?code=...&evidence=open`.

## Data layer (no Firebase)

- **Firestore/Firebase are intentionally not used** (team decision). The PRD's
  `onSnapshot` realtime layer is replaced behind the same `RealtimeClient`
  interface:
  - `mock` mode: an in-memory emitter (`src/mocks/state.ts`) that fires on kiosk
    signals, "next morning" and reset.
  - `live` mode: **HTTP polling** every 5s (`src/lib/realtime/live.ts`).
  Components depend only on `src/lib/realtime/index.ts`, so swapping in
  Firestore later requires no component changes.
- All raw API payloads are `snake_case` and validated with `zod`
  (`src/lib/api/schemas.ts`); conversion to `camelCase` happens only in
  `src/lib/api/adapters.ts`. The UI never reads `true_demand` or `gt_*` fields.
- `NEXT_PUBLIC_DATA_MODE` selects the adapter (`mock` default).

## Assumed API endpoints (to confirm with backend)

These were not fully specified in the build plan (they previously lived in
Firestore). The frontend assumes:

- `GET /api/demo/state` → `{ scenario, last_reset_at }`
- `GET /api/manager/{storeId}/alerts` → `{ alerts: [...] }`
- `GET /api/manager/{storeId}/live-signals` → `{ signals: [...] }`
- List endpoints return envelopes (`{ stores }`, `{ products }`,
  `{ recommendations }`, `{ alerts }`, `{ signals }`).
- `POST /api/demo/reset` and `POST /api/demo/next-morning` return the new
  `{ scenario, last_reset_at }`.

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
  Firebase Hosting) and notes that realtime uses API polling instead of
  Firestore.
- Mock serves the same dataset for every store (Toko 2/3 relabel), sufficient
  for the demo; live mode uses `storeId` from the API.
