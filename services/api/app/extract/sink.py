"""Persist a live extracted signal to BigQuery + the visitor's Firestore sandbox (build plan §6.5).

Only used when DATA_BACKEND=gcp. Google clients are imported lazily so offline/template runs and unit
tests never need them. Base data in BigQuery is never touched here; live signals carry sandbox_id and
land in sandboxes/{id}/** so each judge's demo stays isolated (contract §2).
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

from ..config import settings
from .catalog import load_catalog
from .core import DEMAND_SIGNALS_COLUMNS

UNMET = ("out_of_stock", "not_carried")


def write_signal(row: dict) -> None:
    """Mirror to the sandbox's liveSignals/metrics/alerts first (what the judge watches), then BigQuery."""
    if row.get("sandbox_id"):
        _write_firestore(row)
    _write_bigquery(row)


@lru_cache(maxsize=1)
def _bigquery():
    from google.cloud import bigquery

    return bigquery.Client(project=settings.gcp_project)


@lru_cache(maxsize=1)
def _firestore():
    from google.cloud import firestore

    return firestore.Client(project=settings.gcp_project)


def _write_bigquery(row: dict) -> None:
    table = f"{settings.gcp_project}.{settings.bq_dataset}.demand_signals"
    # row_ids lets BigQuery drop a duplicate insert when Pub/Sub redelivers after a lost response.
    errors = _bigquery().insert_rows_json(table, [{k: row.get(k) for k in DEMAND_SIGNALS_COLUMNS}],
                                          row_ids=[row.get("signal_id")])
    if errors:
        raise RuntimeError(f"demand_signals insert failed: {errors}")


def parse_ts(value) -> dt.datetime | None:
    """ISO string -> aware datetime (stored as a Firestore Timestamp), or None if unparseable."""
    try:
        ts = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)


def live_signal_doc(row: dict) -> dict:
    """Contract §2 liveSignals fields; ts falls back to the server time when the row has none."""
    from google.cloud import firestore

    cat = load_catalog()
    matched, substitute = cat.get(row.get("sku")), cat.get(row.get("substitute_sku"))
    doc = {
        "storeId": row.get("store_id"), "sku": row.get("sku"),
        "requestedText": row.get("requested_text"), "normalizedName": row.get("normalized_name"),
        "outcome": row.get("outcome"), "ts": parse_ts(row.get("ts")) or firestore.SERVER_TIMESTAMP,
        "source": "Kiosk",
    }
    if matched:
        doc["matchedName"] = matched.name
    if substitute:
        doc["substituteName"] = substitute.name
    return doc


def _write_firestore(row: dict) -> None:
    from google.api_core.exceptions import AlreadyExists
    from google.cloud import firestore

    box = _firestore().collection("sandboxes").document(row["sandbox_id"])

    # Keyed by signal_id so a Pub/Sub redelivery neither duplicates the signal nor counts it twice.
    try:
        box.collection("liveSignals").document(row["signal_id"]).create(live_signal_doc(row))
    except AlreadyExists:
        return

    if row.get("outcome") in UNMET:
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
