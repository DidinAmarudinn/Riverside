import pytest

from app.tools.analytics import get_lost_revenue, get_recommendations, get_sku_detail
from app.tools.bq import set_runner
from app.tools.gaps import get_assortment_gaps

from .fake_bq import RECS, FakeRunner


@pytest.fixture
def runner():
    r = FakeRunner()
    set_runner(r)
    return r  # the autouse fixture in conftest restores the default runner afterwards


def use(r):
    set_runner(r)
    return r


# -- get_recommendations -------------------------------------------------------------------------
def test_not_ready_reports_observed_facts_and_says_so(runner):
    res = get_recommendations("S01")
    assert res["status"] == "forecast_not_ready" and "items" not in res
    assert [i["sku"] for i in res["observed_risk"]] == ["SKU-0001", "SKU-0004"]
    assert res["observed_risk"][0]["unmet_requests_7d"] == 14 and res["observed_risk"][0]["on_hand"] == 0
    assert [e["sku"] for e in res["evidence"]] == ["SKU-0001", "SKU-0004"]
    assert all(e["type"] == "sku" and e["store_id"] == "S01" for e in res["evidence"])


def test_with_recommendations_returns_a_b_forecasts_sorted_by_lost_revenue():
    use(FakeRunner(recs=RECS))
    res = get_recommendations("S01")
    assert res["status"] == "ok" and res["run_date"] == "2026-10-12"
    first = res["items"][0]
    assert first["sku"] == "SKU-0001" and (first["recommended_qty_a"], first["recommended_qty_b"]) == (40, 60)
    assert first["forecast_a_7d"] == 84.0 and first["forecast_b_7d"] == 196.0
    assert res["evidence"][0]["recommended_qty_b"] == 60  # the number the UI will cite


def test_risk_filter_and_limit():
    use(FakeRunner(recs=RECS))
    assert [i["sku"] for i in get_recommendations("S01", risk="reorder")["items"]] == ["SKU-0007"]
    assert len(get_recommendations("S01", limit=1)["items"]) == 1
    # a filter that matches nothing falls back to the observed list rather than pretending forecasts exist
    assert get_recommendations("S01", risk="nope")["status"] == "forecast_not_ready"


def test_store_id_is_a_query_parameter_never_part_of_the_sql(runner):
    get_recommendations("S01'; DROP TABLE x; --")
    for sql, params in runner.calls:
        assert "DROP" not in sql and params["store_id"] == "S01'; DROP TABLE x; --"


def test_observed_query_never_touches_ground_truth(runner):
    get_recommendations("S01")
    get_sku_detail("S01", "SKU-0001")
    get_lost_revenue("S01")
    get_assortment_gaps("S01")
    sql = " ".join(s for s, _ in runner.calls).lower()
    assert "true_demand" not in sql and "gt_sku" not in sql and "gt_outcome" not in sql


# -- get_sku_detail ------------------------------------------------------------------------------
def test_sku_detail_by_code_computes_window_totals_in_code(runner):
    res = get_sku_detail("S01", "sku-0001")  # case-insensitive
    assert res["status"] == "ok" and res["sku"] == "SKU-0001"
    assert res["product"]["name"] == "Santan Kotak Kara 65 ml" and res["product"]["aisle"] == "A1-2"
    assert res["stock"] == {"as_of": "2026-10-12", "on_hand": 0, "sold_7d": 0, "sold_28d": 105,
                            "stockout_days_7d": 7, "stockout_days_28d": 7, "unmet_requests_7d": 14,
                            "unmet_requests_28d": 14}
    assert len(res["last_14_days"]) == 14 and res["last_14_days"][0]["is_stockout"] is True
    assert res["recommendation"] is None and res["forecast_available"] is False and res["forecasts"] == []
    assert [e["type"] for e in res["evidence"]] == ["sku", "signal"]
    assert res["evidence"][0]["unmet_requests_7d"] == 14
    assert res["evidence"][1]["quote"] == "santan 65ml ada ?" and res["evidence"][1]["conversation_id"] == "cv-008163"


def test_sku_detail_includes_the_recommendation_when_it_exists():
    use(FakeRunner(recs=RECS))
    res = get_sku_detail("S01", "SKU-0001")
    assert res["recommendation"]["recommended_qty_b"] == 60
    assert res["evidence"][0]["forecast_b_7d"] == 196.0


def test_sku_detail_by_synonym_is_ambiguous_with_most_unmet_first(runner):
    res = get_sku_detail("S01", "santan")
    assert res["status"] == "ambiguous"
    assert [c["sku"] for c in res["candidates"]] == ["SKU-0001", "SKU-0004"]
    assert res["candidates"][0]["unmet_requests_total"] == 39


def test_sku_detail_not_found(runner):
    assert get_sku_detail("S01", "unicorn food")["status"] == "not_found"


# -- get_lost_revenue ----------------------------------------------------------------------------
def test_lost_revenue_totals_and_evidence(runner):
    res = get_lost_revenue("S01", days_ago=1)
    assert res["status"] == "ok" and res["date"] == "2026-10-11"
    assert res["total_lost_revenue_idr"] == 66000 + 9000 and res["total_unmet_qty"] == 5
    assert res["items_affected"] == 2 and res["evidence"][0]["sku"] == "SKU-0211"
    sql, params = runner.calls[0]
    assert params == {"n": 1, "store_id": "S01"} and "S01" not in sql


def test_lost_revenue_all_stores_and_no_data(runner):
    assert get_lost_revenue()["store_id"] == "all" and "store_id" not in runner.calls[-1][1]
    res = get_lost_revenue("S01", days_ago=30)
    assert res["status"] == "no_data" and res["total_lost_revenue_idr"] == 0 and res["evidence"] == []


def test_lost_revenue_rejects_negative_days(runner):
    get_lost_revenue("S01", days_ago=-5)
    assert runner.calls[0][1]["n"] == 0


# -- get_assortment_gaps -------------------------------------------------------------------------
def test_gaps_for_a_store_keep_three_quotes_each(runner):
    res = get_assortment_gaps("S01", limit=3)
    assert res["status"] == "ok" and res["items"][0]["normalized_name"] == "oat milk"
    assert res["items"][0]["sample_requests"] == ["a", "b", "c"]
    assert res["evidence"][0] == {"type": "gap", "store_id": "S01", "normalized_name": "oat milk",
                                  "requests": 12, "quotes": ["a", "b", "c"]}
    sql, params = runner.calls[0]
    assert "WHERE g.store_id = @store_id" in sql and params["n"] == 3


def test_gaps_across_all_stores_aggregate_by_product(runner):
    get_assortment_gaps("", limit=500)
    sql, params = runner.calls[0]
    assert "GROUP BY g.normalized_name" in sql and "store_id =" not in sql and params["n"] == 20  # capped


def test_sku_detail_accepts_english_product_names(runner):
    res = get_sku_detail("S01", "coconut milk")  # catalog names are Indonesian ("santan")
    assert res["status"] == "ambiguous" and res["candidates"][0]["sku"] == "SKU-0001"
