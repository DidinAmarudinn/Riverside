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


def _search(matches):
    return [{"name": "search_products", "args": {}, "result": {"matches": matches}}]


def _m(sku, name, price, units):
    return {"sku": sku, "name": name, "price_idr": price, "units": units, "shelf_location": "A6-1", "match_score": 0.9}


def test_cards_follow_the_reply_for_every_candidate_it_quotes():
    calls = _search([_m("S1", "Beras Medium Bulog 10 kg", 118000, 8), _m("S2", "Beras Medium Bulog 5 kg", 62000, 10),
                     _m("S3", "Beras Pandan Wangi Cianjur 5 kg", 78000, 32), _m("S4", "Beras Merah 1 kg", 21000, 3)])
    reply = ("Ada Beras Medium Bulog 10 kg, Rp 118.000, stok 8. Beras Pandan Wangi 5 kg harganya Rp 78.000, "
             "stoknya 32.")
    skus = [p["sku"] for p in contract.kiosk_payload(calls, reply)["products"]]
    assert skus == ["S1", "S3"]  # S2 / S4 are not talked about; S3 is matched despite the shortened name


def test_without_a_reply_only_the_best_match_gets_a_card():
    calls = _search([_m("S1", "Beras Medium Bulog 10 kg", 118000, 8), _m("S3", "Beras Pandan Wangi 5 kg", 78000, 32)])
    assert [p["sku"] for p in contract.kiosk_payload(calls)["products"]] == ["S1"]


def test_same_price_bystander_is_not_carded():
    calls = _search([_m("S1", "Santan Kotak Sasa 65 ml", 4200, 10), _m("S2", "Kecap Manis ABC 65 ml", 4200, 5)])
    assert [p["sku"] for p in contract.kiosk_payload(calls, "Sasa 65 ml Rp 4.200, stok 10.")["products"]] == ["S1"]


def test_plain_text_removes_markdown_the_ui_would_show_raw():
    raw = ("Berikut rekomendasi:\n*  **Santan Kara 65 ml**: pesan 64 unit.\n* Tomat 500 g: pesan 20.\n"
           "## Rekomendasi\nPrioritaskan `Santan`.")
    out = contract.plain_text(raw)
    assert "*" not in out and "#" not in out and "`" not in out
    assert out.splitlines()[1] == "- Santan Kara 65 ml: pesan 64 unit."
    assert out.splitlines()[2] == "- Tomat 500 g: pesan 20."


def test_plain_text_leaves_normal_replies_alone():
    s = "Santan Kara 65 ml: order 64, not 10 (Rp 4.500)."
    assert contract.plain_text(s) == s
