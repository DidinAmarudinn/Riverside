PY := .venv/bin/python

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
	PYTHONPATH=data $(PY) -m sim.load_bq --project $(PROJECT) --location $(or $(GCP_LOCATION),us-central1)
api:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m uvicorn app.main:app --reload --port 8080
web:
	cd apps/web && npm run dev
test:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m pytest -q
smoke:
	python3 infra/smoke_test.py $(or $(SUITE),judge)
