"""Runtime settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo-root .env for local dev (no-op on Cloud Run, where env vars are set on the service).
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# google-genai / ADK read GOOGLE_CLOUD_*, not our GCP_* names. Without this the location silently falls back to
# "global" (and the project to whatever ADC says), so make our settings the source of truth.
if os.getenv("GCP_PROJECT"):
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.environ["GCP_PROJECT"])
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_LOCATION", "us-central1"))


@dataclass(frozen=True)
class Settings:
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")
    bq_dataset: str = os.getenv("BQ_DATASET", "demand_radar")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Gemini 2.5 thinking budget in tokens: 0 = off (default: much lower latency, see docs/limits.md),
    # -1 = leave it to the model (dynamic thinking), N > 0 = cap.
    gemini_thinking_budget: int = int(os.getenv("GEMINI_THINKING_BUDGET", "0"))
    pubsub_topic: str = os.getenv("PUBSUB_TOPIC", "conversations")
    firestore_collection: str = os.getenv("FIRESTORE_COLLECTION", "signals_live")
    # "local" = CSVs in data/out + in-memory state; "gcp" = BigQuery + Firestore + Pub/Sub
    backend: str = os.getenv("DATA_BACKEND", "local")
    # Service account the manager agent's free-form SQL runs as (read-only on the views). When set, the API
    # impersonates it for query_data; when empty the API's own identity is used (local dev) and only the
    # in-code guards protect the data.
    agent_sql_sa: str = os.getenv("AGENT_SQL_SA", "")
    # Where finished turns go: "local" = in memory, "pubsub" = the Pub/Sub topic (must exist; see infra/pubsub.sh).
    # Independent of DATA_BACKEND so BigQuery data can be used before the topic is created.
    publisher: str = os.getenv("PUBLISHER", "local")
    # Repo `data/` directory (product master, seed_scenarios.yaml, and simulator output in data/out)
    data_dir: Path = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    )


settings = Settings()
