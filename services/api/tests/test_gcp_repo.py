"""GcpRepo against a fake BigQuery client (no network): checks the SQL contract and the row mapping."""
import pytest

from app.data import set_repo
from app.data.gcp import GcpRepo
from app.tools.products import search_products
from app.tools.stock import check_stock, find_alternatives, nearest_branch_with_stock

PRODUCT_ROWS = [
    dict(sku="SNT-001", name="Nyiur Santan Kotak 65 ml", brand="Nyiur", category="coconut_milk",
         aisle="Lorong 3 - Bumbu Dapur", pack_size=65.0, unit="ml", price_idr=4500, shelf_life_days=270,
         synonyms=["santan", "santen", "santan kotak", "santan kecil", "santan kotak kecil"]),
    dict(sku="SNT-002", name="Nyiur Santan Kotak 200 ml", brand="Nyiur", category="coconut_milk",
         aisle="Lorong 3 - Bumbu Dapur", pack_size=200.0, unit="ml", price_idr=12000, shelf_life_days=270,
         synonyms=["santan", "santen", "santan kotak", "santan sedang"]),
    dict(sku="SNT-006", name="Kelapaku Santan Kotak 200 ml", brand="Kelapaku", category="coconut_milk",
         aisle="Lorong 3 - Bumbu Dapur", pack_size=200.0, unit="ml", price_idr=12000, shelf_life_days=270,
         synonyms=["santan", "santan kotak", "santan sedang"]),
    dict(sku="SNT-004", name="Nyiur Santan Bubuk 20 g", brand="Nyiur", category="coconut_milk",
         aisle="Lorong 3 - Bumbu Dapur", pack_size=20.0, unit="g", price_idr=3500, shelf_life_days=270,
         synonyms=["santan bubuk", "santan sachet"]),
    dict(sku="TLR-001", name="Telur Ayam Negeri 10 butir", brand="", category="eggs", aisle=None,
         pack_size=10.0, unit="butir", price_idr=28000, shelf_life_days=21, synonyms=["telur", "telor ayam"]),
]
STORE_ROWS = [
    dict(store_id="S01", name="Toko 1 - Tebet", city="Jakarta Selatan", lat=-6.2265, lng=106.8535),
    dict(store_id="S02", name="Toko 2 - Kemang", city="Jakarta Selatan", lat=-6.2607, lng=106.8136),
    dict(store_id="S03", name="Toko 3 - Margonda", city="Depok", lat=-6.3725, lng=106.8343),
]
STOCK_ROWS = [  # S01: santan kotak 65/200 empty, Kelapaku 200 in stock
    *[dict(store_id="S01", sku=s, closing_stock=u) for s, u in
      [("SNT-001", 0), ("SNT-002", 0), ("SNT-006", 12), ("SNT-004", 30), ("TLR-001", 9)]],
    *[dict(store_id="S02", sku=s, closing_stock=u) for s, u in
      [("SNT-001", 40), ("SNT-002", 5), ("SNT-006", 0), ("SNT-004", 3), ("TLR-001", 0)]],
    *[dict(store_id="S03", sku=s, closing_stock=u) for s, u in
      [("SNT-001", 7), ("SNT-002", 0), ("SNT-006", 0), ("SNT-004", 0), ("TLR-001", 4)]],
]


class FakeBQ:
    def __init__(self):
        self.queries: list[str] = []

    def query(self, sql, job_config=None):
        self.queries.append(sql)
        self.job_config = job_config
        rows = (PRODUCT_ROWS if "product_master" in sql else STORE_ROWS if ".stores" in sql
                else STOCK_ROWS if "stock_events" in sql else [])
        return type("Job", (), {"result": lambda self_: rows})()


@pytest.fixture
def gcp():
    bq = FakeBQ()
    repo = GcpRepo("proj", "ds", client=bq, max_bytes_billed=12345)
    set_repo(repo)
    yield repo, bq
    set_repo(None)


def test_queries_are_scoped_and_capped(gcp):
    repo, bq = gcp
    assert all("`proj.ds`" in q for q in bq.queries)
    assert any("WHERE is_carried" in q for q in bq.queries)  # items the store does not sell are not searchable
    assert any("MAX(date)" in q for q in bq.queries)  # live stock = latest day
    assert bq.job_config.maximum_bytes_billed == 12345


def test_product_mapping(gcp):
    repo, _ = gcp
    p = repo.get_product("SNT-001")
    assert p["pack_size"] == "65 ml" and p["shelf_location"] == "Lorong 3 - Bumbu Dapur" and p["price_idr"] == 4500
    assert repo.get_product("TLR-001")["shelf_location"] == "" and repo.get_product("TLR-001")["brand"] == ""
    assert repo.get_product("NC-001") is None


def test_distance_is_haversine_between_store_coordinates(gcp):
    repo, _ = gcp
    assert repo.distance_km("S01", "S01") == 0
    assert repo.distance_km("S01", "S02") == repo.distance_km("S02", "S01")
    assert 4 < repo.distance_km("S01", "S02") < 6  # Tebet-Kemang, ~5 km straight line
    assert repo.distance_km("S01", "S99") is None


def test_live_stock_overrides_and_reset(gcp):
    repo, _ = gcp
    assert repo.get_stock("S01", "SNT-001") == 0
    repo.set_stock("S01", "SNT-001", 60)
    assert repo.get_stock("S01", "SNT-001") == 60
    repo.reset_live_stock()
    assert repo.get_stock("S01", "SNT-001") == 0
    with pytest.raises(KeyError):
        repo.set_stock("S01", "NC-001", 1)


def test_tools_work_on_bigquery_shaped_data(gcp):
    top = search_products("santan kecil")["matches"][0]
    assert top["sku"] == "SNT-001" and top["match_score"] >= 0.8  # catalog synonym "santan kecil"
    assert check_stock("S01", "SNT-001")["status"] == "out_of_stock"
    alts = [a["sku"] for a in find_alternatives("S01", "SNT-001")["alternatives"]]
    assert alts == ["SNT-006"]  # carton coconut milk in stock; powder (SNT-004) is not a substitute
    branches = nearest_branch_with_stock("S01", "SNT-001")["branches"]
    assert [b["store_id"] for b in branches] == ["S02", "S03"] and branches[0]["units"] == 40


def test_search_is_robust_to_filler_and_typos(gcp):
    for q in ("pak stok santan kosong ya?", "punten mas santen kotak aya teu", "nyari satnan bubuk di rak mana"):
        assert search_products(q)["matches"], q
    assert search_products("nyari satnan bubuk di rak mana")["matches"][0]["sku"] == "SNT-004"
    assert search_products("telornya ada gak kak")["matches"][0]["sku"] == "TLR-001"


def test_unsold_item_is_not_matched_even_with_filler(gcp):
    for q in ("ada susu oat gak kak?", "mas saus tiram ready ga", "punten gula aren cair aya teu"):
        assert [m for m in search_products(q)["matches"] if m["match_score"] >= 0.8] == [], q
