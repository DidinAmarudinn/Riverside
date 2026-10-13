"""Runtime settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")
    bq_dataset: str = os.getenv("BQ_DATASET", "demand_radar")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    pubsub_topic: str = os.getenv("PUBSUB_TOPIC", "conversations")
    firestore_collection: str = os.getenv("FIRESTORE_COLLECTION", "signals_live")
    # "local" = CSVs in data/out + in-memory state; "gcp" = BigQuery + Firestore + Pub/Sub
    backend: str = os.getenv("DATA_BACKEND", "local")
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    )


settings = Settings()
