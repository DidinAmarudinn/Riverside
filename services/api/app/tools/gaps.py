"""Assortment gap analysis: products shoppers ask for but the store does not sell."""
from __future__ import annotations

from .bq import get_runner


def fetch_gaps(runner, store_id: str, n: int) -> list[dict]:
    """Gap rows per product name, most requested first, with the latest shopper wording.

    v_assortment_gaps has one row per (store, category, name) and the extractor leaves category null about half
    of the time, so the same product shows up twice: rows are merged by name here (category = any non-null one).
    """
    fq = runner.fq
    params: dict = {"n": n}
    # latest shopper wording per product, joined in (BigQuery does not support correlated ARRAY_AGG subqueries)
    # v_signals = one signal per conversation (extractor rows win over the bootstrap seed), base data only
    base = f"{fq}.v_signals WHERE outcome = 'not_carried'"
    where = "WHERE g.store_id = @store_id" if store_id else ""
    if store_id:
        params["store_id"] = store_id
        base += " AND store_id = @store_id"
    sql = (f"WITH q AS (SELECT normalized_name, ARRAY_AGG(requested_text ORDER BY ts DESC LIMIT 3) AS sample_requests "
           f"FROM {base} GROUP BY normalized_name) "
           f"SELECT g.normalized_name, MAX(g.category) AS category, SUM(g.requests) AS requests, "
           f"MIN(g.first_seen) AS first_seen, MAX(g.last_seen) AS last_seen, ANY_VALUE(q.sample_requests) AS sample_requests "
           f"FROM {fq}.v_assortment_gaps g LEFT JOIN q USING (normalized_name) {where} "
           f"GROUP BY g.normalized_name ORDER BY requests DESC, g.normalized_name LIMIT @n")
    items = runner.rows(sql, params)
    for it in items:
        it["sample_requests"] = (it.get("sample_requests") or [])[:3]
    return items


def get_assortment_gaps(store_id: str = "", limit: int = 10) -> dict:
    """Products shoppers ask for that the store does not carry, most requested first.

    Names come from the signal extractor and can contain spelling variants of the same product ("oat milk",
    "oat mulk"); mention it when two entries look like the same thing.

    Args:
        store_id: Store code, or empty to combine all stores.
        limit: Maximum number of products (default 10, max 20).

    Returns:
        {status, items: [{normalized_name, category, requests, first_seen, last_seen, sample_requests}],
        evidence: [...]}
    """
    items = fetch_gaps(get_runner(), store_id, max(1, min(int(limit), 20)))
    return {
        "status": "ok" if items else "no_data", "store_id": store_id or "all", "items": items,
        "evidence": [{"type": "gap", "store_id": store_id or "all", "normalized_name": it["normalized_name"],
                      "requests": it["requests"], "quotes": it["sample_requests"]} for it in items],
    }
