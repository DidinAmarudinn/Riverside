"""Assortment gap analysis: products shoppers ask for but the store does not sell."""
from __future__ import annotations

from .bq import get_runner


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
    n = max(1, min(int(limit), 20))
    runner = get_runner()
    fq = runner.fq
    params: dict = {"n": n}
    # latest shopper wording per product, joined in (BigQuery does not support correlated ARRAY_AGG subqueries)
    base = f"{fq}.demand_signals WHERE sandbox_id IS NULL AND outcome = 'not_carried'"
    if store_id:
        params["store_id"] = store_id
        sql = (f"WITH q AS (SELECT store_id, normalized_name, ARRAY_AGG(requested_text ORDER BY ts DESC LIMIT 3) "
               f"AS sample_requests FROM {base} GROUP BY store_id, normalized_name) "
               f"SELECT g.normalized_name, g.category, g.requests, g.first_seen, g.last_seen, q.sample_requests "
               f"FROM {fq}.v_assortment_gaps g LEFT JOIN q USING (store_id, normalized_name) "
               f"WHERE g.store_id = @store_id ORDER BY g.requests DESC, g.normalized_name LIMIT @n")
    else:
        sql = (f"WITH q AS (SELECT normalized_name, ARRAY_AGG(requested_text ORDER BY ts DESC LIMIT 3) "
               f"AS sample_requests FROM {base} GROUP BY normalized_name) "
               f"SELECT g.normalized_name, ANY_VALUE(g.category) AS category, SUM(g.requests) AS requests, "
               f"MIN(g.first_seen) AS first_seen, MAX(g.last_seen) AS last_seen, ANY_VALUE(q.sample_requests) AS sample_requests "
               f"FROM {fq}.v_assortment_gaps g LEFT JOIN q USING (normalized_name) "
               f"GROUP BY g.normalized_name ORDER BY requests DESC, g.normalized_name LIMIT @n")
    items = runner.rows(sql, params)
    for it in items:
        it["sample_requests"] = (it.get("sample_requests") or [])[:3]
    return {
        "status": "ok" if items else "no_data", "store_id": store_id or "all", "items": items,
        "evidence": [{"type": "gap", "store_id": store_id or "all", "normalized_name": it["normalized_name"],
                      "requests": it["requests"], "quotes": it["sample_requests"]} for it in items],
    }
