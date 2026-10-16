PY := .venv/bin/python

# Load local .env (KEY=value) so GCP_PROJECT / GCP_LOCATION etc. are available to the targets
# below and exported to the processes they spawn. CLI overrides still win (e.g. make load GCP_PROJECT=x).
ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: setup product-master sim extract eval load forecast experiment sync-firestore api web test smoke e2e e2e-gaps
setup:
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt pytest nbformat
	cd apps/web && npm install
product-master:
	PYTHONPATH=data $(PY) -m sim.build_product_master
sim:
	PYTHONPATH=data $(PY) -m sim.run
# Signal extraction over the generated conversations (LLM=gemini for the real extractor).
extract:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.extract.batch --llm $(or $(LLM),template)
eval:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.extract.eval
# Load CSVs + build tables/views in BigQuery (needs GCP creds and PROJECT=<id>).
load:
	@test -n "$(strip $(GCP_PROJECT))" || { echo "GCP_PROJECT is empty — set it in .env or pass GCP_PROJECT=<id>"; exit 1; }
	PYTHONPATH=data $(PY) -m sim.load_bq --project $(strip $(GCP_PROJECT)) --location $(strip $(or $(GCP_LOCATION),us-central1))
# Forecast A vs B and recommendations (build plan step 7). Needs `make load` first; re-run after every reload of the data.
# Trains BigQuery ML models (about a minute, a few cents), so it is not part of `make load`.
forecast:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.pipeline series
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.pipeline train
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.pipeline forecast
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.pipeline recommend
# Backtest, order-policy replay and ask-rate sensitivity -> docs/results.md
experiment:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.experiment
# Copy recommendations and KPIs to the Firestore base collections (add ARGS=--dry-run to preview)
sync-firestore:
	cd services/api && DATA_BACKEND=gcp PYTHONPATH=.:../../data ../../$(PY) -m app.forecast.sync_firestore $(ARGS)
api:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m uvicorn app.main:app --reload --port 8080
web:
	cd apps/web && npm run dev
test:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m pytest -q
smoke:
	python3 infra/smoke_test.py $(or $(SUITE),judge)
# Playwright against the deployed site (BASE_URL overrides). e2e = invariants that must pass; e2e-gaps = open findings.
e2e:
	cd apps/web && npm run e2e
e2e-gaps:
	cd apps/web && npm run e2e:gaps
