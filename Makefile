PY := .venv/bin/python

.PHONY: setup product-master sim api web test smoke
setup:
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt pytest nbformat
	cd apps/web && npm install
product-master:
	PYTHONPATH=data $(PY) -m sim.build_product_master
sim:
	PYTHONPATH=data $(PY) -m sim.run
api:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m uvicorn app.main:app --reload --port 8080
web:
	cd apps/web && npm run dev
test:
	cd services/api && PYTHONPATH=.:../../data ../../$(PY) -m pytest -q
smoke:
	python3 infra/smoke_test.py $(or $(SUITE),judge)
