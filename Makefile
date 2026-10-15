PY := .venv/bin/python

# Load local .env (KEY=value) so GCP_PROJECT / GCP_LOCATION etc. are available to the targets
# below and exported to the processes they spawn. CLI overrides still win (e.g. make load GCP_PROJECT=x).
ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: setup product-master sim extract eval load api web test smoke
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
api:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m uvicorn app.main:app --reload --port 8080
web:
	cd apps/web && npm run dev
test:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m pytest -q
smoke:
	python3 infra/smoke_test.py $(or $(SUITE),judge)
