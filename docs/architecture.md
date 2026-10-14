# Architecture

```
[Kiosk (React)] ──HTTPS──> Firebase Hosting ──/api/**──> [Cloud Run: demand-radar-api (FastAPI + ADK)]
                                                          ├─ shopper agent (search, stock, alternatives, branches)
                                                          ├─ manager agent (recommendations, SKU detail, read-only SQL, gaps)
                                                          └─ publish conversation ──> [Pub/Sub: conversations]
                                                                                          │ push with OIDC (dr-pubsub-invoker)
                                       /pubsub/extract <──────────────────────────────────┘  (straight to Cloud Run)
                                          └─ Gemini structured output + outcome rules
                                               ├─> BigQuery demand_signals (+ BQML forecasts A/B, recommendations)
                                               └─> Firestore sandboxes/{sandboxId}/liveSignals, alerts, metrics
[Manager dashboard (React)] <── Firestore onSnapshot (read-only) ───────────────────────────────┘
```

- One Cloud Run service (`demand-radar-api`, service account `dr-api`) for the API, both agents and the extractor.
- Hosting rewrites only `/api/**`; `/pubsub/extract` is reached by Pub/Sub directly and verifies the OIDC token.
- Per-visitor sandboxes: the browser sends `X-Sandbox-Id`; everything a demo changes is written under
  `sandboxes/{sandboxId}`. Base data in BigQuery and Firestore is shared and read-only.
- Region: `us-central1` for Cloud Run, Firestore, BigQuery and Vertex AI.

Contract: `docs/api-contract.md`.
