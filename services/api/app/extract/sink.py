"""Persist a live extracted signal to BigQuery + the visitor's Firestore sandbox (build plan §6.5).

Only used when DATA_BACKEND=gcp. Google clients are imported lazily so offline/template runs and unit
tests never need them. Base data in BigQuery is never touched here; live signals carry sandbox_id and
land in sandboxes/{id}/** so each judge's demo stays isolated (contract §2).
"""
from __future__ import annotations

from ..config import settings
from .core import DEMAND_SIGNALS_COLUMNS

UNMET = ("out_of_stock", "not_carried")


def write_signal(row: dict) -> None:
    """Insert into demand_signals, then mirror to the sandbox's liveSignals/metrics/alerts."""
    _write_bigquery(row)
    if row.get("sandbox_id"):
        _write_firestore(row)


def _write_bigquery(row: dict) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=settings.gcp_project)
    table = f"{settings.gcp_project}.{settings.bq_dataset}.demand_signals"
    errors = client.insert_rows_json(table, [{k: row.get(k) for k in DEMAND_SIGNALS_COLUMNS}])
    if errors:
        raise RuntimeError(f"demand_signals insert failed: {errors}")


def _write_firestore(row: dict) -> None:
    from google.cloud import firestore

    db = firestore.Client(project=settings.gcp_project)
    box = db.collection("sandboxes").document(row["sandbox_id"])

    box.collection("liveSignals").add({
        "storeId": row.get("store_id"), "sku": row.get("sku"),
        "requestedText": row.get("requested_text"), "normalizedName": row.get("normalized_name"),
        "outcome": row.get("outcome"), "ts": row.get("ts"),
    })

    if row.get("outcome") in UNMET and row.get("outcome") != "low_confidence":
        metrics = box.collection("metrics").document(row.get("store_id") or "unknown")
        metrics.set({"unmetToday": firestore.Increment(int(row.get("qty") or 1))}, merge=True)
        box.collection("alerts").add({
            "storeId": row.get("store_id"), "sku": row.get("sku"),
            "type": "unmet_spike" if row.get("outcome") == "out_of_stock" else "reorder",
            "severity": "medium",
            "title": f"Permintaan tak terpenuhi: {row.get('normalized_name') or row.get('requested_text')}",
            "body": f"Shopper mencari '{row.get('requested_text')}' ({row.get('outcome')}).",
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
