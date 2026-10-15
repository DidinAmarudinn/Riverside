import pytest

from app.tools.analytics import get_lost_revenue, get_recommendations, get_sku_detail
from app.tools.bq import set_runner
from app.tools.gaps import get_assortment_gaps

from .fake_bq import SUMMARY_NOT_READY, FakeRunner, with_recs


@pytest.fixture
def runner():
    r = FakeRunner()
    set_runner(r)
    yield r
    set_runner(None)


def use(r):
    set_runner(r)
    return r


# -- get_recommendations -------------------------------------------------------------------------
def test_not_ready_reports_observed_facts_and_says_so(runner):
    res = get_recommendations("S01")
    assert res["status"] == "forecast_not_ready" and "items" not in res
    skus = [i["sku"] for i in res["observed_risk"]]
    assert skus == ["SNT-001", "SNT-002"]  # sorted by unmet demand; the healthy egg SKU is left out
    assert res["observed_risk"][0]["est_unmet_units_7d"] == 112.5
    assert [e["sku"] for e in res["evidence"]] == skus and all(e["type"] == "sku" for e in res["evidence"])


def test_with_recommendations_returns_a_b_forecasts_sorted_by_lost_revenue():
    use(FakeRunner(summary=with_recs(SUMMARY_NOT_READY)))
    res = get_recommendations("S01")
    assert res["status"] == "ok"
    first = res["items"][0]
    assert first["sku"] == "SNT-001" and (first["recommended_qty_a"], first["recommended_qty_b"]) == (40, 60)
    assert first["forecast_a_7d"] == 84.0 and first["forecast_b_7d"] == 196.0
    assert res["evidence"][0]["recommended_qty_b"] == 60  # the number the UI will cite
    set_runner(None)


def test_risk_filter_and_limit():
    use(FakeRunner(summary=with_recs(SUMMARY_NOT_READY)))
    assert [i["sku"] for i in get_recommendations("S01", risk="ok")["items"]] == ["TLR-001"]
    assert len(get_recommendations("S01", limit=1)["items"]) == 1
    assert len(get_recommendations("S01", limit=999)["items"]) <= 10
    set_runner(None)


def test_store_id_is_a_query_parameter_never_part_of_the_sql(runner):
    get_recommendations("S01'; DROP TABLE x; --")
    sql, params = runner.calls[0]
    assert "DROP" not in sql and "@store_id" in sql and params == {"store_id": "S01'; DROP TABLE x; --"}


# -- get_sku_detail ------------------------------------------------------------------------------
def test_sku_detail_by_code_collects_summary_daily_quotes_and_forecast_flag(runner):
    res = get_sku_detail("S01", "snt-001")  # case-insensitive
    assert res["status"] == "ok" and res["sku"] == "SNT-001"
    assert res["summary"]["unmet_signals_7d"] == 45 and res["daily"][0]["is_stockout"] is True
    assert res["forecast_available"] is False and res["forecasts"] == []
    types = [e["type"] for e in res["evidence"]]
    assert types == ["sku", "signal"] and res["evidence"][1]["quote"] == "santan 65ml ada ?"
    assert res["evidence"][1]["conversation_id"] == "cv-008163"


def test_sku_detail_by_unique_name(runner):
    assert get_sku_detail("S01", "telur ayam")["sku"] == "TLR-001"


def test_sku_detail_by_category_is_ambiguous_with_most_unmet_first(runner):
    res = get_sku_detail("S01", "coconut milk")
    assert res["status"] == "ambiguous"
    assert [c["sku"] for c in res["candidates"]] == ["SNT-001", "SNT-002"]


def test_sku_detail_not_found(runner):
    assert get_sku_detail("S01", "unicorn food")["status"] == "not_found"


# -- get_lost_revenue ----------------------------------------------------------------------------
def test_lost_revenue_totals_and_evidence(runner):
    res = get_lost_revenue("S01", days_ago=1)
    assert res["status"] == "ok" and res["date"] == "2026-10-13"
    assert res["total_lost_revenue_idr"] == 165000 + 11250 and res["total_unmet_units"] == 10.0
    assert res["items_affected"] == 2 and res["evidence"][0]["sku"] == "ROT-006"
    sql, params = runner.calls[0]
    assert params == {"n": 1, "store_id": "S01"} and "S01" not in sql


def test_lost_revenue_all_stores_and_no_data(runner):
    assert "store_id" not in runner.calls and get_lost_revenue()["store_id"] == "all"
    assert "store_id" not in runner.calls[-1][1]
    res = get_lost_revenue("S01", days_ago=30)
    assert res["status"] == "no_data" and res["total_lost_revenue_idr"] == 0 and res["evidence"] == []


def test_lost_revenue_rejects_negative_days(runner):
    get_lost_revenue("S01", days_ago=-5)
    assert runner.calls[0][1]["n"] == 0


# -- get_assortment_gaps -------------------------------------------------------------------------
def test_gaps_for_a_store_keep_three_quotes_each(runner):
    res = get_assortment_gaps("S01", limit=3)
    assert res["status"] == "ok" and res["items"][0]["normalized_name"] == "susu oat 1 l"
    assert res["items"][0]["sample_requests"] == ["a", "b", "c"]
    assert res["evidence"][0] == {"type": "gap", "store_id": "S01", "normalized_name": "susu oat 1 l",
                                  "requests_28d": 51, "requests_total": 142, "quotes": ["a", "b", "c"]}
    sql, params = runner.calls[0]
    assert "WHERE store_id = @store_id" in sql and params["n"] == 3


def test_gaps_across_all_stores_aggregate_by_product(runner):
    get_assortment_gaps("", limit=500)
    sql, params = runner.calls[0]
    assert "GROUP BY normalized_name" in sql and "store_id =" not in sql and params["n"] == 20  # capped
