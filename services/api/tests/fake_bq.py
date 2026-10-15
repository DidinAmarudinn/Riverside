"""In-memory stand-in for BqRunner: routes queries by a substring of the SQL, records what was asked."""
from __future__ import annotations

from app.tools.sqlguard import ALLOWED_VIEWS

SUMMARY_NOT_READY = [  # v_sku_summary rows before the forecast pipeline has produced recommendations
    dict(store_id="S01", sku="SNT-001", name="Nyiur Santan Kotak 65 ml", category="coconut_milk", aisle="L3",
         price_idr=4500, on_hand=0, is_stockout_today=True, sold_7d=12, sold_28d=257, avg_daily_sold_instock_28d=20.8,
         stockout_days_7d=7, stockout_days_28d=18, unmet_signals_7d=45, est_unmet_units_7d=112.5, rec_run_date=None,
         forecast_a_7d=None, forecast_b_7d=None, recommended_qty_a=None, recommended_qty_b=None, risk_type=None,
         lost_revenue_idr=None, reason_text=None),
    dict(store_id="S01", sku="SNT-002", name="Nyiur Santan Kotak 200 ml", category="coconut_milk", aisle="L3",
         price_idr=12000, on_hand=0, is_stockout_today=True, sold_7d=0, sold_28d=100, avg_daily_sold_instock_28d=9.0,
         stockout_days_7d=7, stockout_days_28d=10, unmet_signals_7d=11, est_unmet_units_7d=27.5, rec_run_date=None,
         forecast_a_7d=None, forecast_b_7d=None, recommended_qty_a=None, recommended_qty_b=None, risk_type=None,
         lost_revenue_idr=None, reason_text=None),
    dict(store_id="S01", sku="TLR-001", name="Telur Ayam Negeri 10 butir", category="eggs", aisle="C1",
         price_idr=28000, on_hand=40, is_stockout_today=False, sold_7d=50, sold_28d=200, avg_daily_sold_instock_28d=7.0,
         stockout_days_7d=0, stockout_days_28d=0, unmet_signals_7d=0, est_unmet_units_7d=0.0, rec_run_date=None,
         forecast_a_7d=None, forecast_b_7d=None, recommended_qty_a=None, recommended_qty_b=None, risk_type=None,
         lost_revenue_idr=None, reason_text=None),
]


def with_recs(rows):
    out = []
    for r in rows:
        r = dict(r)
        if r["sku"] == "SNT-001":
            r.update(rec_run_date="2026-10-14", forecast_a_7d=84.0, forecast_b_7d=196.0, recommended_qty_a=40,
                     recommended_qty_b=60, risk_type="stockout", lost_revenue_idr=506250,
                     reason_text="POS-only forecast misses 112 unmet units")
        elif r["sku"] == "TLR-001":
            r.update(rec_run_date="2026-10-14", forecast_a_7d=55.0, forecast_b_7d=55.0, recommended_qty_a=20,
                     recommended_qty_b=20, risk_type="ok", lost_revenue_idr=0, reason_text="steady")
        out.append(r)
    return out


class FakeRunner:
    project, dataset = "proj", "ds"
    fq = "`proj.ds`"
    _max_bytes = 1_000_000

    def __init__(self, summary=None, dry=None, agent_result=None, agent_error=None):
        self.summary = SUMMARY_NOT_READY if summary is None else summary
        self.calls: list[tuple[str, dict]] = []
        self.agent_sql: list[str] = []
        self._dry = dry or {"statement_type": "SELECT", "tables": {"pos_sales"}, "bytes": 1000}
        self._agent_result = agent_result if agent_result is not None else [{"n": 1}]
        self._agent_error = agent_error

    # fixed, parametrised queries
    def rows(self, sql, params=None):
        self.calls.append((sql, dict(params or {})))
        p = params or {}
        if "FROM `proj.ds`.v_sku_summary" in sql and "LOWER(name) LIKE" in sql:
            q = p["q"].strip("%")
            hits = [r for r in self.summary if r["store_id"] == p["s"]
                    and (q in r["name"].lower() or q in r["category"].replace("_", " "))]
            hits.sort(key=lambda r: (-(r["est_unmet_units_7d"] or 0), r["sku"]))
            return [dict(r) for r in hits[:5]]
        if "FROM `proj.ds`.v_sku_summary" in sql and "sku = @k" in sql and "SELECT sku, name" in sql:
            return [{"sku": r["sku"], "name": r["name"]} for r in self.summary
                    if r["store_id"] == p["s"] and r["sku"] == p["k"]]
        if "FROM `proj.ds`.v_sku_summary" in sql and "sku = @k" in sql:
            return [dict(r) for r in self.summary if r["store_id"] == p["s"] and r["sku"] == p["k"]]
        if "FROM `proj.ds`.v_sku_summary" in sql:
            return [dict(r) for r in self.summary if r["store_id"] == p["store_id"]]
        if "v_unmet_daily" in sql and "ORDER BY date DESC" in sql:
            return [dict(date="2026-10-14", qty_sold=0, closing_stock=0, is_stockout=True, unmet_signals=9,
                         est_unmet_units=22.5)]
        if "v_evidence" in sql:
            return [dict(date="2026-10-14", ts="2026-10-14 11:44:44", outcome="out_of_stock",
                         requested_text="santan 65ml ada ?", conversation_id="cv-008163", channel="kiosk")]
        if ".forecasts" in sql:
            return []
        if "v_unmet_daily u JOIN" in sql:
            if p.get("n", 0) > 5:
                return []
            return [dict(date="2026-10-13", store_id="S01", sku="ROT-006", name="Roti Pagi", is_stockout=True,
                         unmet_signals=3, est_unmet_units=7.5, price_idr=22000, est_lost_revenue_idr=165000),
                    dict(date="2026-10-13", store_id="S01", sku="SNT-001", name="Santan 65", is_stockout=True,
                         unmet_signals=1, est_unmet_units=2.5, price_idr=4500, est_lost_revenue_idr=11250)]
        if "v_assortment_gaps" in sql:
            item = dict(normalized_name="susu oat 1 l", category="dairy", requests_total=142, requests_7d=11,
                        requests_28d=51, first_seen="2026-07-21", last_seen="2026-10-14",
                        sample_requests=["a", "b", "c", "d"])
            return [item]
        raise AssertionError(f"unrouted SQL: {sql}")

    # free-form agent SQL
    def agent_dry_run(self, sql):
        self.agent_sql.append(sql)
        return self._dry

    def allowed_lineage(self):
        return {"pos_sales", "conversations", "demand_signals", "product_master", "stock_events"}

    def agent_rows(self, sql):
        if self._agent_error:
            raise self._agent_error
        return self._agent_result


FakeRunner.view_columns = lambda self: {
    "v_sku_summary": ["store_id STRING", "sku STRING", "on_hand INTEGER"],
    "v_unmet_daily": ["date DATE", "store_id STRING", "is_stockout BOOLEAN"],
}
