"""In-memory stand-in for BqRunner: routes queries by a fragment of the SQL, records what was asked.

Data mirrors the rebuilt dataset: hero SKU-0001 is empty in S01 (7 days out, 2 unmet requests a day), the sibling
SKU-0004 is out for one day.
"""
from __future__ import annotations

HERO = dict(sku="SKU-0001", name="Santan Kotak Kara 65 ml", brand="Kara", category="Cooking Essentials",
            pack_size="65 ml", price_idr=4500, aisle="A1-2", shelf_life_days=270)

OBSERVED = [  # get_recommendations fallback rows (no forecasts yet)
    dict(sku="SKU-0001", name="Santan Kotak Kara 65 ml", price_idr=4500, on_hand=0, stockout_days_7d=7,
         unmet_requests_7d=14),
    dict(sku="SKU-0004", name="Santan Kotak Sasa 65 ml", price_idr=4200, on_hand=3, stockout_days_7d=1,
         unmet_requests_7d=0),
]

RECS = [  # v_sku_summary once the forecast pipeline has run
    dict(run_date="2026-10-12", store_id="S01", sku="SKU-0001", on_hand=0, forecast_a_7d=84.0, forecast_b_7d=196.0,
         unmet_7d=14, recommended_qty_a=40, recommended_qty_b=60, risk_type="stockout_risk", lost_revenue_idr=63000,
         reason_text="POS-only forecast misses 14 unmet requests", name="Santan Kotak Kara 65 ml", brand="Kara",
         category="Cooking Essentials", pack_size="65 ml", price_idr=4500, shelf_life_days=270, aisle="A1-2"),
    dict(run_date="2026-10-12", store_id="S01", sku="SKU-0007", on_hand=14, forecast_a_7d=55.0, forecast_b_7d=55.0,
         unmet_7d=0, recommended_qty_a=20, recommended_qty_b=20, risk_type="reorder", lost_revenue_idr=0,
         reason_text="steady", name="Minyak Goreng Bimoli 2 L", brand="Bimoli", category="Cooking Essentials",
         pack_size="2 L", price_idr=37000, shelf_life_days=540, aisle="A2-4"),
]


def hero_days():
    days = []
    for i in range(28):
        day = 12 - i
        date = f"2026-10-{day:02d}" if day >= 1 else f"2026-09-{30 + day:02d}"
        out = i < 7
        days.append(dict(date=date, qty_sold=0 if out else 5, closing_stock=0 if out else 20, is_stockout=out,
                         unmet_requests=2 if out else 0))
    return days


class FakeRunner:
    project, dataset = "proj", "ds"
    fq = "`proj.ds`"
    _max_bytes = 1_000_000

    def __init__(self, recs=None, dry=None, agent_result=None, agent_error=None):
        self.recs = recs or []
        self.calls: list[tuple[str, dict]] = []
        self.agent_sql: list[str] = []
        self._dry = dry or {"statement_type": "SELECT", "tables": {"pos_sales"}, "bytes": 1000}
        self._agent_result = agent_result if agent_result is not None else [{"n": 1}]
        self._agent_error = agent_error

    # fixed, parametrised queries -------------------------------------------------------------------
    def rows(self, sql, params=None):
        self.calls.append((sql, dict(params or {})))
        p = params or {}
        if "v_sku_summary WHERE store_id = @store_id" in sql:
            return [dict(r) for r in self.recs if r["store_id"] == p["store_id"]]
        if "v_sku_summary WHERE store_id = @s AND sku = @k" in sql:
            return [dict(r) for r in self.recs if r["store_id"] == p["s"] and r["sku"] == p["k"]]
        if "stockout_days_7d" in sql and "WITH d AS" in sql:  # observed-risk fallback
            return [dict(r) for r in OBSERVED][: p["n"]]
        if "product_master WHERE is_carried AND sku = @k" in sql:
            return [{"sku": HERO["sku"], "name": HERO["name"]}] if p["k"] == "SKU-0001" else []
        if "LOWER(p.name) LIKE @q" in sql:
            q = p["q"].strip("%")
            table = [("SKU-0001", HERO["name"], 39), ("SKU-0004", "Santan Kotak Sasa 65 ml", 2),
                     ("SKU-0007", "Minyak Goreng Bimoli 2 L", 0)]
            hits = [dict(sku=s, name=n, unmet_requests_total=u) for s, n, u in table if q in n.lower() or q == "santan" and "santan" in n.lower()]
            return hits[:5]
        if "FROM `proj.ds`.product_master WHERE sku = @k" in sql:
            return [dict(HERO)]
        if "stock_events e LEFT JOIN" in sql:
            return hero_days()
        if ".v_evidence" in sql:
            return [dict(date="2026-10-12", ts="2026-10-12 11:44:44", outcome="out_of_stock",
                         requested_text="santan 65ml ada ?", conversation_id="cv-008163", channel="kiosk")]
        if ".forecasts" in sql:
            return []
        if "v_unmet_daily u JOIN" in sql:  # get_lost_revenue
            if p.get("n", 0) > 5:
                return []
            return [dict(date="2026-10-11", store_id="S01", sku="SKU-0211", name="Roti Tawar", unmet_qty=3,
                         price_idr=22000, lost_revenue_idr=66000),
                    dict(date="2026-10-11", store_id="S01", sku="SKU-0001", name="Santan Kotak Kara 65 ml",
                         unmet_qty=2, price_idr=4500, lost_revenue_idr=9000)]
        if "v_assortment_gaps" in sql:
            return [dict(normalized_name="oat milk", category=None, requests=12, first_seen="2026-07-18",
                         last_seen="2026-09-30", sample_requests=["a", "b", "c", "d"])]
        raise AssertionError(f"unrouted SQL: {sql}")

    # free-form agent SQL ---------------------------------------------------------------------------
    def agent_dry_run(self, sql):
        self.agent_sql.append(sql)
        return self._dry

    def allowed_lineage(self):
        return {"pos_sales", "conversations", "demand_signals", "product_master", "stock_events", "recommendations"}

    def agent_rows(self, sql):
        if self._agent_error:
            raise self._agent_error
        return self._agent_result

    def view_columns(self):
        return {
            "v_unmet_daily": ["date DATE", "store_id STRING", "unmet_qty INTEGER"],
            "v_sku_summary": ["store_id STRING", "sku STRING", "on_hand INTEGER"],
        }
