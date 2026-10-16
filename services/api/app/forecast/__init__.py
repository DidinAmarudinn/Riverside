"""Forecast A vs B and reorder recommendations (build plan step 7).

Pure logic (ask rate estimate, B series, reorder formula, risk flags, policy simulation, WAPE) lives in plain
modules with unit tests; `pipeline.py` and `experiment.py` run them against BigQuery / BigQuery ML.
"""
