import csv
from pathlib import Path

import pytest

from app.data import set_repo
from app.data.local import LocalRepo
from app.tools.products import search_products
from app.tools.stock import check_stock, find_alternatives, nearest_branch_with_stock

REAL_DATA = Path(__file__).resolve().parents[3] / "data"


def names(res):
    return [m["name"] for m in res["matches"]]


# -- search_products -----------------------------------------------------------------------------
def test_search_finds_product_with_shelf_and_price(world):
    res = search_products("santan kara 65 ml")
    top = res["matches"][0]
    assert res["status"] == "ok" and top["sku"] == "SKU-0001"
    assert top["match_score"] >= 0.8 and top["price_idr"] == 4500 and top["shelf_location"] == "A1-2"


def test_search_handles_slang_and_spelling(world):
    assert names(search_products("migor 2 liter"))[0].startswith("Minyak Goreng")
    assert names(search_products("telor ayam")) == ["Telur Ayam Peternak Lokal 10 pcs"]
    assert names(search_products("mie goreng"))[0].startswith("Mi Goreng")


def test_search_ignores_filler_words(world):
    assert names(search_products("kak ada santan kecil dong"))[0].startswith("Santan Kotak")


def test_search_unsold_product_returns_no_match(world):
    for q in ("oat milk", "salmon fillet", "sambal ijo"):
        res = search_products(q)
        assert res["status"] == "no_match" and res["matches"] == [], q


def test_search_blank_or_only_filler_is_no_match(world):
    assert search_products("")["status"] == "no_match"
    assert search_products("ada dong kak")["status"] == "no_match"


def test_search_respects_limit(world):
    assert len(search_products("santan", limit=2)["matches"]) == 2


@pytest.mark.skipif(not (REAL_DATA / "out" / "stock_events.csv").exists(), reason="run `make sim` first")
def test_real_catalog_never_matches_items_the_store_does_not_sell():
    set_repo(LocalRepo(REAL_DATA))
    try:
        not_sold = [r["item"] for r in csv.DictReader(open(REAL_DATA / "not_stocked_items.csv", encoding="utf-8"))]
        assert len(not_sold) >= 10
        hits = {item: names(search_products(item)) for item in not_sold if search_products(item)["matches"]}
        assert hits == {}
    finally:
        set_repo(None)


# -- check_stock ---------------------------------------------------------------------------------
def test_check_stock_in_stock(world):
    r = check_stock("S01", "SKU-0008")
    assert r["status"] == "in_stock" and r["units"] == 100 and r["shelf_location"] == "B1-1"


def test_check_stock_out_and_low(world):
    assert check_stock("S01", "SKU-0001")["status"] == "out_of_stock"  # hero scenario
    assert check_stock("S01", "SKU-0006")["status"] == "low_stock"  # 4 units


def test_check_stock_unknown(world):
    assert check_stock("S01", "SKU-9999") == {"status": "unknown", "sku": "SKU-9999", "store_id": "S01"}
    assert check_stock("S99", "SKU-0001")["status"] == "unknown"


# -- find_alternatives ---------------------------------------------------------------------------
def test_alternatives_same_subcategory_in_stock_and_not_itself(world):
    res = find_alternatives("S01", "SKU-0001")
    skus = [a["sku"] for a in res["alternatives"]]
    assert res["status"] == "ok"
    assert "SKU-0001" not in skus and "SKU-0004" not in skus  # itself / out of stock at S01
    assert set(skus) <= {"SKU-0002", "SKU-0003"} and skus  # coconut milk only
    assert skus[0] == "SKU-0003"  # same pack size beats same brand but bigger/pricier


def test_alternatives_none_when_whole_subcategory_empty(world):
    world.set_stock("S01", "SKU-0002", 0)
    world.set_stock("S01", "SKU-0003", 0)
    assert find_alternatives("S01", "SKU-0001") == {"status": "none", "alternatives": []}


def test_alternatives_unknown_sku(world):
    assert find_alternatives("S01", "SKU-9999")["status"] == "none"


# -- nearest_branch_with_stock ------------------------------------------------------------------
def test_nearest_branch_sorted_by_distance_and_excludes_own_store(world):
    res = nearest_branch_with_stock("S01", "SKU-0001")
    assert res["status"] == "found"
    assert [b["store_id"] for b in res["branches"]] == ["S02", "S03"]
    assert res["branches"][0] == {"store_id": "S02", "name": "Radar Mart BSD", "distance_km": 21.0, "units": 40}


def test_nearest_branch_skips_branches_without_stock(world):
    assert [b["store_id"] for b in nearest_branch_with_stock("S01", "SKU-0002")["branches"]] == ["S02"]  # S03 has 0
    assert nearest_branch_with_stock("S01", "SKU-0004") == {"status": "none", "branches": []}
