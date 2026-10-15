# Demand Radar

> POS data tells you what sold. Conversations tell you what people wanted.

An AI agent that reads shopper conversations in grocery stores to capture demand that never reached the POS
(censored demand), then uses it for more accurate forecasts and reorder advice.
Built on Google Cloud (Gemini, ADK, BigQuery ML, Cloud Run, Firebase) for AI Builder Cup 2026.
All data is synthetic.

## Layout

```
apps/web/        Next.js (static export): kiosk, manager dashboard, judges page
services/api/    FastAPI + ADK agents, tools, extraction, demo sandbox
data/            product master, simulator (sim/), scenarios
sql/             BigQuery DDL, views, ARIMA_PLUS models, evaluation
notebooks/       experiment.ipynb
infra/           Firestore rules, Firebase config, deploy + Pub/Sub scripts
docs/            architecture, API contract, experiment results
```

## Quick start

```bash
make setup            # venv + Python deps + npm install
make product-master   # (re)build data/product_master.csv (214 SKUs)
make api              # http://localhost:8080/api/healthz
make web              # http://localhost:3000
```

Copy `.env.example` to `.env` and fill in the GCP values to enable Gemini and the `gcp` backend.

## Status

Scaffold: project structure, API stubs (health + placeholder routes), ADK agent definitions, web routes,
BigQuery DDL, infra scripts. Product catalog and a first simulator draft (`data/sim/`) exist; forecasting,
extraction, agent tools and UI are not implemented yet.
