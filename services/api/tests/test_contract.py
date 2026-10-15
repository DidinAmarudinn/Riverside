from app import contract


def test_strip_markers_leaves_clean_prose():
    assert contract.strip_markers("Out of stock [E1], with 112 unmet [E2, E3].") == "Out of stock, with 112 unmet."
    assert contract.strip_markers("No markers here.") == "No markers here."
    assert contract.strip_markers("Two [E1] [E2] cites") == "Two cites"


def test_kiosk_payload_dedupes_and_ignores_unknown_stock():
    calls = [
        {"name": "check_stock", "result": {"status": "unknown", "sku": "X", "store_id": "S01"}},
        {"name": "check_stock", "result": {"status": "in_stock", "sku": "A", "name": "A", "units": 3,
                                           "price_idr": 100, "shelf_location": "A1"}},
        {"name": "check_stock", "result": {"status": "in_stock", "sku": "A", "name": "A", "units": 3,
                                           "price_idr": 100, "shelf_location": "A1"}},
        {"name": "find_alternatives", "result": {"status": "none", "alternatives": []}},
        {"name": "nearest_branch_with_stock", "result": {"status": "none", "branches": []}},
    ]
    out = contract.kiosk_payload(calls)
    assert [p["sku"] for p in out["products"]] == ["A"] and out["alternatives"] == [] and out["nearestBranch"] is None


def test_citation_shapes():
    assert contract.citation({"type": "sku", "id": "E1", "sku": "S-1", "name": "Santan"}) == {"label": "Santan", "sku": "S-1"}
    sig = contract.citation({"type": "signal", "date": "2026-10-14", "sku": "S-1", "quote": "santan ada?"})
    assert sig == {"label": "Shopper request · 2026-10-14", "quote": "santan ada?", "sku": "S-1", "date": "2026-10-14"}
    gap = contract.citation({"type": "gap", "normalized_name": "oat milk", "quotes": ["ada oat?"]})
    assert gap == {"label": "oat milk", "quote": "ada oat?"}
    assert contract.citation({"type": "query", "sql": "SELECT  1\nFROM v"})["label"] == "Query: SELECT 1 FROM v"


def test_kiosk_payload_reads_stock_and_rescue_from_a_store_search():
    best = {"sku": "A", "name": "A", "shelf_location": "A1", "price_idr": 10, "units": 0, "stock_status": "out_of_stock"}
    other = {**best, "sku": "B", "units": 4}
    alt = {"sku": "C", "name": "C", "shelf_location": "A2", "price_idr": 9, "units": 7}
    branch = {"store_id": "S02", "name": "BSD", "distance_km": 21, "units": 12}
    out = contract.kiosk_payload([{"name": "search_products", "result": {
        "matches": [best, other], "alternatives": [alt], "nearest_branch": branch}}])
    assert [(p["sku"], p["inStock"]) for p in out["products"]] == [("A", False)]  # the product the reply is about
    assert [a["sku"] for a in out["alternatives"]] == ["C"]
    assert out["nearestBranch"] == {"storeId": "S02", "name": "BSD", "distanceKm": 21, "stockQty": 12}
