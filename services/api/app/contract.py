"""Translate agent output into the response objects of docs/api-contract.md §3.1 (camelCase).

The agents work with tool results and numbered evidence; the contract (and the frontend) want KioskProduct /
Branch / Citation objects and a reply without [E#] markers.
"""
from __future__ import annotations

import re

_MARKER = re.compile(r"\s*\[E\d+(?:\s*,\s*E\d+)*\]")


def strip_markers(reply: str) -> str:
    """'Santan is out [E1, E2].' -> 'Santan is out.' (the markers are for the citations list, not for display)."""
    return re.sub(r"\s+([.,;:!?])", r"\1", _MARKER.sub("", reply)).strip()


def _kiosk_product(item: dict, units: int | None, in_stock: bool) -> dict:
    out = {"sku": item["sku"], "name": item["name"], "inStock": in_stock, "aisle": item.get("shelf_location", "")}
    if item.get("price_idr") is not None:
        out["priceIdr"] = item["price_idr"]
    if units is not None:
        out["stockQty"] = units
    return out


def kiosk_payload(tool_calls: list[dict]) -> dict:
    """products / alternatives / nearestBranch from the shopper tools called in this turn."""
    products, alternatives, branch = {}, {}, None
    for call in tool_calls:
        res = call.get("result") or {}
        if call["name"] == "search_products" and res.get("matches") and "units" in res["matches"][0]:
            best = res["matches"][0]  # searched with the store: the product the reply is about
            if best["units"] is not None:
                products[best["sku"]] = _kiosk_product(best, best["units"], best["units"] > 0)
            for alt in res.get("alternatives") or []:
                alternatives[alt["sku"]] = _kiosk_product(alt, alt["units"], True)
            b = res.get("nearest_branch")
            if b and branch is None:
                branch = {"storeId": b["store_id"], "name": b["name"], "distanceKm": b["distance_km"], "stockQty": b["units"]}
        elif call["name"] == "check_stock" and res.get("status") in ("in_stock", "low_stock", "out_of_stock"):
            products[res["sku"]] = _kiosk_product(res, res["units"], res["units"] > 0)
        elif call["name"] == "find_alternatives":
            for alt in res.get("alternatives", []):
                alternatives[alt["sku"]] = _kiosk_product(alt, alt["units"], True)
        elif call["name"] == "nearest_branch_with_stock" and res.get("branches") and branch is None:
            b = res["branches"][0]
            branch = {"storeId": b["store_id"], "name": b["name"], "distanceKm": b["distance_km"], "stockQty": b["units"]}
    return {"products": list(products.values()), "alternatives": list(alternatives.values()), "nearestBranch": branch}


def citation(ev: dict) -> dict:
    """One evidence item -> Citation {label, sku?, date?, quote?}."""
    kind = ev.get("type")
    if kind == "sku":
        out = {"label": ev.get("name") or ev.get("sku", "")}
    elif kind == "signal":
        out = {"label": f"Shopper request · {ev.get('date', '')}".strip(" ·"), "quote": ev.get("quote")}
    elif kind == "gap":
        quotes = ev.get("quotes") or []
        out = {"label": ev.get("normalized_name", ""), "quote": quotes[0] if quotes else None}
    elif kind == "query":
        out = {"label": "Query: " + re.sub(r"\s+", " ", ev.get("sql", ""))[:80]}
    else:
        out = {"label": str(ev.get("id", "source"))}
    if ev.get("sku"):
        out["sku"] = ev["sku"]
    if ev.get("date"):
        out["date"] = ev["date"]
    return {k: v for k, v in out.items() if v not in (None, "")}


def citations(evidence: list[dict]) -> list[dict]:
    return [citation(e) for e in evidence]
