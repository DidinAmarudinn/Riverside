"""Copy the recommendation and KPI base data from BigQuery to the shared Firestore collections (build plan 7.9).

    python -m app.forecast.sync_firestore [--dry-run] [--prune]

Writes docs/api-contract.md section 2 base data: `recommendations/{storeId}_{sku}` (a Recommendation) for every flagged
SKU, and `metrics/{storeId}` (lostRevenueToday, unmetToday, stockoutSkus). The documents are produced by the same
functions as the API's GET routes, so the dashboard shows identical numbers either way. Per-visitor results ("next
morning") are written to the visitor's sandbox elsewhere, never here. Safe to re-run: documents are overwritten by id.
"""
from __future__ import annotations

import argparse

from .. import manager_api

BATCH = 400  # Firestore allows 500 writes per batch


def build(store_ids: list[str]) -> tuple[dict[str, dict], dict[str, dict]]:
    recs, metrics = {}, {}
    for store in store_ids:
        for r in manager_api.recommendations(store)["items"]:
            recs[f"{r['storeId']}_{r['sku']}"] = r
        metrics[store] = manager_api.overview(store)["kpis"]
    return recs, metrics


def sync(db, recs: dict[str, dict], metrics: dict[str, dict], prune: bool = False, dry_run: bool = False) -> dict[str, int]:
    """Write the documents; with `prune`, delete base documents that are no longer in the new set."""
    counts = {"recommendations_written": len(recs), "metrics_written": len(metrics), "recommendations_pruned": 0}
    stale: list = []
    if prune:
        stale = [d for d in db.collection("recommendations").list_documents() if d.id not in recs]
        counts["recommendations_pruned"] = len(stale)
    if dry_run:
        return counts
    ops = [(db.collection("recommendations").document(i), doc) for i, doc in recs.items()]
    ops += [(db.collection("metrics").document(i), doc) for i, doc in metrics.items()]
    for start in range(0, len(ops), BATCH):
        batch = db.batch()
        for ref, doc in ops[start:start + BATCH]:
            batch.set(ref, doc)
        batch.commit()
    for start in range(0, len(stale), BATCH):
        batch = db.batch()
        for ref in stale[start:start + BATCH]:
            batch.delete(ref)
        batch.commit()
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="count what would be written, write nothing")
    ap.add_argument("--prune", action="store_true", help="also delete recommendation documents that are no longer flagged")
    args = ap.parse_args()
    from google.cloud import firestore

    from ..config import settings
    from ..data import get_repo

    recs, metrics = build([s["id"] for s in get_repo().stores()])
    counts = sync(firestore.Client(project=settings.gcp_project), recs, metrics, prune=args.prune, dry_run=args.dry_run)
    print(("dry run: " if args.dry_run else "") + ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
