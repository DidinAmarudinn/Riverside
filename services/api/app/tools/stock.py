"""Stock lookups (tool functions for the agents).

All numbers the shopper agent quotes (stock, price, shelf) come from these functions, never from the model.
"""
from __future__ import annotations

import math

from ..data import get_repo
from .text import kind_tokens, pack_of

LOW_STOCK_THRESHOLD = 5
KIND_OVERLAP = 0.5  # share of name words (minus brand/size) two products must have in common


def _brief(product: dict) -> dict:
    return {
        "sku": product["sku"], "name": product["name"], "pack_size": product["pack_size"],
        "price_idr": product["price_idr"], "shelf_location": product["shelf_location"],
    }


def check_stock(store_id: str, sku: str) -> dict:
    """Check how many units of a product are on the shelf in a store, and where to find it.

    Args:
        store_id: Store code, e.g. "S01".
        sku: Product code from `search_products`, e.g. "SKU-0001".

    Returns:
        {status: "in_stock" | "low_stock" | "out_of_stock" | "unknown", sku, name, store_id, units,
        price_idr, shelf_location}. `status` is "unknown" when the store or SKU does not exist.
    """
    repo = get_repo()
    product = repo.get_product(sku)
    units = repo.get_stock(store_id, sku)
    if product is None or units is None:
        return {"status": "unknown", "sku": sku, "store_id": store_id}
    status = "out_of_stock" if units == 0 else "low_stock" if units <= LOW_STOCK_THRESHOLD else "in_stock"
    return {"status": status, "store_id": store_id, "units": units, **_brief(product)}


def _substitution_penalty(orig: dict, cand: dict) -> float:
    """Lower is a closer substitute: same unit and size first, then same brand, then similar price."""
    po, pc = pack_of(orig), pack_of(cand)
    if po and pc and po[1] == pc[1]:
        size = 0.2 * abs(math.log(pc[0] / po[0])) if po[0] and pc[0] else 0.3
    else:
        size = 0.5
    brand = 0.1 * (cand["brand"] != orig["brand"])
    price = 0.1 * min(abs(cand["price_idr"] - orig["price_idr"]) / max(orig["price_idr"], 1), 3)
    return size + brand + price


def find_alternatives(store_id: str, sku: str, limit: int = 3) -> dict:
    """Find similar products that are in stock in this store (use when the wanted product is empty).

    A substitute must be the same kind of product (e.g. another carton coconut milk, not coconut milk
    powder). Closest pack size comes first, then same brand, then similar price. Never returns the product
    itself.

    Args:
        store_id: Store code, e.g. "S01".
        sku: Product code that is out of stock.
        limit: Maximum number of alternatives.

    Returns:
        {status: "ok" | "none", alternatives: [{sku, name, pack_size, price_idr, shelf_location, units}]}
    """
    repo = get_repo()
    product = repo.get_product(sku)
    if product is None:
        return {"status": "none", "alternatives": []}
    kind = kind_tokens(product)
    ranked = []
    for p in repo.products():
        if p["sku"] == sku or p["category"] != product["category"]:
            continue
        other = kind_tokens(p)
        if not kind or len(kind & other) / len(kind | other) < KIND_OVERLAP:
            continue
        units = repo.get_stock(store_id, p["sku"])
        if not units:
            continue
        ranked.append((_substitution_penalty(product, p), p, units))
    ranked.sort(key=lambda r: (r[0], r[1]["name"]))
    alts = [{**_brief(p), "units": u} for _, p, u in ranked[: max(1, min(limit, 5))]]
    return {"status": "ok" if alts else "none", "alternatives": alts}


def nearest_branch_with_stock(store_id: str, sku: str) -> dict:
    """Find the closest other branch that has this product in stock (distance is approximate, straight line).

    Args:
        store_id: The store the shopper is in (excluded from the search).
        sku: Product code.

    Returns:
        {status: "found" | "none", branches: [{store_id, name, distance_km, units}]} sorted nearest first.
    """
    repo = get_repo()
    found = []
    for other, units in repo.stock_by_store(sku).items():
        if other == store_id or units <= 0:
            continue
        km = repo.distance_km(store_id, other)
        store = repo.get_store(other) or {}
        found.append({"store_id": other, "name": store.get("name", other), "distance_km": km, "units": units})
    found.sort(key=lambda b: (b["distance_km"] is None, b["distance_km"] or 0))
    return {"status": "found" if found else "none", "branches": found}
