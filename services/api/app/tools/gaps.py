"""Assortment gap analysis: products shoppers ask for but the store does not sell."""
from __future__ import annotations

import weakref

from .bq import get_runner
from .products import _same_word
from .text import tokens


RAW_LIMIT = 500  # raw (store, name) rows read before spelling variants are merged


def _not_carried(runner) -> list[tuple[tuple[str, ...], str, str | None]]:
    """(synonym tokens, catalog name, category) for products the store does not sell, longest synonym first.

    product_master lists them with is_carried = false and the spellings shoppers use ("oat mulk", "susu oat").
    """
    if runner not in _NC_CACHE:
        table = []
        for r in runner.rows(f"SELECT name, category, synonyms FROM {runner.fq}.product_master "
                             f"WHERE NOT is_carried", {}):
            for syn in {r["name"], *(r.get("synonyms") or [])}:
                if tokens(syn):
                    table.append((tuple(tokens(syn)), r["name"], r.get("category")))
        _NC_CACHE[runner] = sorted(table, key=lambda t: -len(t[0]))
    return _NC_CACHE[runner]


_NC_CACHE: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def canonical_gap(name: str, table) -> tuple[str, str | None] | None:
    """The catalog product a raw gap name refers to: a synonym appearing as whole words in it, typos allowed
    the same way product search allows them ("sambal hijau tidak", "almond miilk"), else None."""
    toks = tuple(tokens(name))
    for syn, product, category in table:
        for i in range(len(toks) - len(syn) + 1):
            if all(_same_word(q, s) > 0 for q, s in zip(toks[i:i + len(syn)], syn)):
                return product, category
    return None


def fetch_gaps(runner, store_id: str, n: int) -> list[dict]:
    """Gap rows per product, most requested first, with the latest shopper wording.

    v_assortment_gaps has one row per (store, category, name) as the extractor wrote it, so one product shows
    up under several spellings ("oat milk", "oatmilk", "oat mulk") and often without a category. Rows are
    merged here under the catalog name of the not-carried product (with its category) when one matches;
    `aliases` keeps the raw names.
    """
    fq = runner.fq
    params: dict = {"n": RAW_LIMIT}
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
    table = _not_carried(runner)
    merged: dict[str, dict] = {}
    for row in runner.rows(sql, params):  # most requested spelling first, so its quotes lead
        match = canonical_gap(row["normalized_name"], table)
        key, category = match if match else (row["normalized_name"], None)
        it = merged.setdefault(key, {"normalized_name": key, "category": category, "requests": 0,
                                     "first_seen": row["first_seen"], "last_seen": row["last_seen"],
                                     "sample_requests": [], "aliases": []})
        it["category"] = it["category"] or row.get("category")
        it["requests"] += row["requests"]
        it["first_seen"] = min(it["first_seen"], row["first_seen"])
        it["last_seen"] = max(it["last_seen"], row["last_seen"])
        it["sample_requests"] += [q for q in row.get("sample_requests") or [] if q not in it["sample_requests"]]
        it["aliases"].append(row["normalized_name"])
    items = sorted(merged.values(), key=lambda it: (-it["requests"], it["normalized_name"]))[:n]
    for it in items:
        it["sample_requests"] = it["sample_requests"][:3]
    return items


def get_assortment_gaps(store_id: str = "", limit: int = 10) -> dict:
    """Products shoppers ask for that the store does not carry, most requested first.

    Spelling variants of a known product ("oat milk", "oat mulk", "susu oat") are merged under its catalog name;
    other names come as the signal extractor wrote them.

    Args:
        store_id: Store code, or empty to combine all stores.
        limit: Maximum number of products (default 10, max 20).

    Returns:
        {status, items: [{normalized_name, category, requests, first_seen, last_seen, sample_requests, aliases}],
        evidence: [...]}
    """
    items = fetch_gaps(get_runner(), store_id, max(1, min(int(limit), 20)))
    return {
        "status": "ok" if items else "no_data", "store_id": store_id or "all", "items": items,
        "evidence": [{"type": "gap", "store_id": store_id or "all", "normalized_name": it["normalized_name"],
                      "requests": it["requests"], "quotes": it["sample_requests"]} for it in items],
    }
