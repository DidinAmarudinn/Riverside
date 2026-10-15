"""Demo sandbox: one-click reset of a visitor's demo (contract §2 `sandboxes/{sandboxId}`).

Everything a visitor's demo writes lives under `sandboxes/{id}` in Firestore (liveSignals, metrics, alerts,
recommendations, sessions). Reset deletes those subcollections and stamps the sandbox doc; base data in
Firestore and BigQuery is never touched (the BigQuery views read `sandbox_id IS NULL` only).
"""
from __future__ import annotations

from ..config import settings

SCENARIO = "Selasa malam"


def reset_sandbox(sandbox_id: str, db=None) -> int:
    """Delete every subcollection of sandboxes/{sandbox_id}, then mark the reset. Returns docs deleted."""
    if db is None:
        if settings.backend != "gcp":
            return 0
        from ..extract.sink import _firestore

        db = _firestore()
    from google.cloud import firestore

    box = db.collection("sandboxes").document(sandbox_id)
    deleted = sum(db.recursive_delete(sub) for sub in box.collections())
    fresh = {"scenario": SCENARIO, "lastResetAt": firestore.SERVER_TIMESTAMP}
    if not box.get().exists:
        fresh["createdAt"] = firestore.SERVER_TIMESTAMP
    box.set(fresh, merge=True)
    return deleted
