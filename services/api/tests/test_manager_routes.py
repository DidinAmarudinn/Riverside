"""Manager GET routes: response shapes follow docs/api-contract.md §3.1 (checked like the web app's zod schemas)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app import main
from app.tools.bq import set_runner

from .fake_bq import FORECASTS, RECS, FakeRunner

H = {"X-Sandbox-Id": str(uuid.uuid4())}
RISKS = {"stockout_risk", "overstock", "reorder", "unmet_spike"}
OUTCOMES = {"purchased", "out_of_stock", "not_carried", "substituted"}
client = TestClient(main.app)


def get(path, runner=None):
    set_runner(runner or FakeRunner())
    return client.get(path, headers=H)


def check_recommendation(r):
    assert {"storeId", "sku", "name", "category", "onHand", "forecastA7d", "forecastB7d", "unmet7d",
            "recommendedQtyA", "recommendedQtyB", "riskType", "lostRevenueIdr", "reasonText"} <= r.keys()
    assert r["riskType"] in RISKS
    for k in ("onHand", "forecastA7d", "forecastB7d", "unmet7d", "recommendedQtyA", "recommendedQtyB", "lostRevenueIdr"):
        assert isinstance(r[k], (int, float)), k


# -- stores / products ---------------------------------------------------------------------------
def test_stores_have_the_required_fields():
    items = client.get("/api/stores").json()["items"]
    assert [s["storeId"] for s in items] == ["S01", "S02", "S03"]
    assert all({"storeId", "name", "city", "lat", "lng"} <= s.keys() for s in items)


def test_products_list_and_search():
    everything = client.get("/api/products").json()["items"]
    assert len(everything) == 8 and everything[0]["isCarried"] is True and everything[0]["unit"] == "ml"
    hits = client.get("/api/products", params={"q": "santan kara kecil"}).json()["items"]
    assert "SKU-0001" in [h["sku"] for h in hits] and {"sku", "name", "priceIdr", "packSize", "aisle"} <= hits[0].keys()
    assert client.get("/api/products", params={"q": "oat milk"}).json()["items"] == []


# -- overview / recommendations ------------------------------------------------------------------
def test_overview_without_recommendations_has_kpis_and_no_risks():
    body = get("/api/manager/S01/overview").json()
    assert body["storeId"] == "S01" and body["kpis"] == {"lostRevenueToday": 9000, "unmetToday": 2, "stockoutSkus": 1}
    assert body["topRisks"] == []  # nothing is invented while the forecast pipeline has not run


def test_overview_and_recommendations_with_forecasts():
    r = FakeRunner(recs=RECS)
    top = get("/api/manager/S01/overview", r).json()["topRisks"]
    assert [t["sku"] for t in top] == ["SKU-0001", "SKU-0007"]
    for t in top:
        check_recommendation(t)
    items = get("/api/manager/S01/recommendations", r).json()["items"]
    assert items[0]["recommendedQtyB"] == 60 and items[0]["recommendedQtyA"] == 40  # most at risk first
    assert [i["sku"] for i in get("/api/manager/S01/recommendations?risk=reorder", r).json()["items"]] == ["SKU-0007"]
    assert get("/api/manager/S01/recommendations").json() == {"storeId": "S01", "items": []}


# -- sku detail ----------------------------------------------------------------------------------
def test_sku_detail_shape_without_forecasts():
    d = get("/api/manager/S01/sku/SKU-0001").json()
    assert {"storeId", "sku", "product", "riskType", "kpis", "sales", "forecastA", "forecastB", "unmetDaily",
            "evidence", "reason"} <= d.keys()
    assert d["riskType"] == "stockout_risk"  # derived from the observed empty shelf
    assert d["product"] == {"name": "Santan Kotak Kara 65 ml", "brand": "Kara", "category": "Cooking Essentials",
                            "packSize": "65 ml", "priceIdr": 4500, "aisle": "A1-2"}
    k = d["kpis"]
    assert (k["onHand"], k["stockoutDays"], k["unmetRequests"], k["lostRevenueUnits"]) == (0, 7, 14, 14)
    assert k["lostRevenueIdr"] == 14 * 4500 and k["stockoutSince"] == "2026-10-06"
    assert len(d["sales"]) == 28 and d["sales"][0]["date"] < d["sales"][-1]["date"]  # oldest first
    assert d["sales"][-1] == {"date": "2026-10-12", "qty": 0, "isStockout": True}
    assert d["unmetDaily"][-1] == {"date": "2026-10-12", "count": 2} and len(d["unmetDaily"]) == 7
    assert d["forecastA"] == [] and d["forecastB"] == []
    assert d["reason"]["recommendedQtyB"] == 0 and "No forecast" in d["reason"]["reasonText"]
    ev = d["evidence"]
    assert ev["total"] == 39 and ev["items"][0] == {
        "id": "cv-008163", "ts": "2026-10-12T11:44:44", "channel": "kiosk", "quote": "santan 65ml ada ?",
        "outcome": "out_of_stock", "confidence": 0.98}
    assert all(e["outcome"] in OUTCOMES for e in ev["items"])


def test_sku_detail_with_recommendation_and_forecast_series():
    d = get("/api/manager/S01/sku/SKU-0001", FakeRunner(recs=RECS, forecasts=FORECASTS)).json()
    assert d["riskType"] == "stockout_risk" and d["kpis"]["lostRevenueIdr"] == 63000  # the pipeline's own number
    assert d["reason"] == {"recommendedQtyA": 40, "recommendedQtyB": 60,
                           "reasonText": "POS-only forecast misses 14 unmet requests"}
    assert d["forecastA"][0] == {"date": "2026-10-13", "qty": 0.0, "lower": 0.0, "upper": 1.0}
    assert [p["qty"] for p in d["forecastB"]] == [8.0, 9.0]  # separate series on their own dates


def test_unknown_sku_is_404_in_the_uniform_error_format():
    r = get("/api/manager/S01/sku/SKU-9999")
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message"}
    assert get("/api/manager/S99/overview").json()["error"]["code"] == "store_not_found"


# -- gaps ----------------------------------------------------------------------------------------
def test_gaps_shape_series_trend_and_revenue():
    body = get("/api/manager/S01/gaps").json()
    assert body["storeId"] == "S01"
    oat, tea = body["items"]
    assert {"name", "category", "requests", "firstSeen", "lastSeen", "daily", "trend7dPct"} <= oat.keys()
    assert oat["name"] == "oat milk" and oat["category"] == "Other" and oat["requests"] == 12
    assert len(oat["daily"]) == 14 and oat["daily"][13] == 2 and oat["daily"][4] == 1  # oldest first
    assert oat["trend7dPct"] == 100  # 2 requests in the last 7 days vs 1 in the 7 before
    assert oat["quote"] == "a" and "estRevenueIdr" not in oat  # no category -> no revenue guess
    assert tea["category"] == "Beverages" and tea["estRevenueIdr"] == 4 * 8500 and "quote" not in tea


# -- failures ------------------------------------------------------------------------------------
class Down(FakeRunner):
    def rows(self, sql, params=None):
        raise RuntimeError("bigquery unreachable")


@pytest.mark.parametrize("path", ["/api/manager/S01/overview", "/api/manager/S01/recommendations",
                                  "/api/manager/S01/sku/SKU-0001", "/api/manager/S01/gaps"])
def test_bigquery_outage_is_a_uniform_503(path):
    r = get(path, Down())
    assert r.status_code == 503 and r.json()["error"]["code"] == "data_unavailable"


def test_sandbox_header_is_still_required():
    assert client.get("/api/manager/S01/overview").status_code == 400
