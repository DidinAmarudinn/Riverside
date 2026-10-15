"""Assortment gap analysis: products shoppers ask for but the store does not sell."""
from __future__ import annotations

from .bq import get_runner


def get_assortment_gaps(store_id: str = "", limit: int = 10) -> dict:
    """Products shoppers ask for that the store does not carry, most requested first.

    Args:
        store_id: Store code, or empty to combine all stores.
        limit: Maximum number of products (default 10, max 20).

    Returns:
        {status, items: [{normalized_name, category, requests_7d, requests_28d, requests_total, first_seen,
        last_seen, sample_requests}], evidence: [...]}
    """
    n = max(1, min(int(limit), 20))
    runner = get_runner()
    fq = runner.fq
    params: dict = {"n": n}
    if store_id:
        params["store_id"] = store_id
        sql = (f"SELECT normalized_name, category, requests_total, requests_7d, requests_28d, first_seen, "
               f"last_seen, sample_requests FROM {fq}.v_assortment_gaps WHERE store_id = @store_id "
               f"ORDER BY requests_28d DESC, requests_total DESC LIMIT @n")
    else:
        sql = (f"SELECT normalized_name, ANY_VALUE(category) AS category, SUM(requests_total) AS requests_total, "
               f"SUM(requests_7d) AS requests_7d, SUM(requests_28d) AS requests_28d, MIN(first_seen) AS first_seen, "
               f"MAX(last_seen) AS last_seen, ARRAY_CONCAT_AGG(sample_requests) AS sample_requests "
               f"FROM {fq}.v_assortment_gaps GROUP BY normalized_name "
               f"ORDER BY requests_28d DESC, requests_total DESC LIMIT @n")
    items = runner.rows(sql, params)
    for it in items:
        it["sample_requests"] = (it.get("sample_requests") or [])[:3]
    return {
        "status": "ok" if items else "no_data", "store_id": store_id or "all", "items": items,
        "evidence": [{"type": "gap", "store_id": store_id or "all", "normalized_name": it["normalized_name"],
                      "requests_28d": it["requests_28d"], "requests_total": it["requests_total"],
                      "quotes": it["sample_requests"]} for it in items],
    }
