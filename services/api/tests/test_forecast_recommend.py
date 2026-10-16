import datetime as dt

import numpy as np
import pandas as pd
import pytest

from app.forecast.recommend import COLUMNS, build_recommendations
from app.forecast.reason import add_reason_text, facts_for, numbers_grounded, template_reason

RUN = dt.date(2026, 10, 13)


def inputs():
    """Two series in one store: SKU-HERO (empty shelf, shoppers asking) and SKU-OK (healthy)."""
    days = pd.date_range("2026-09-29", "2026-10-12")
    facts = pd.concat([
        pd.DataFrame(dict(date=days, store_id="S01", sku="SKU-HERO", category="Cooking Essentials", unmet_signals=2.0)),
        pd.DataFrame(dict(date=days, store_id="S01", sku="SKU-OK", category="Cooking Essentials", unmet_signals=0.0)),
    ], ignore_index=True)
    fdays = pd.date_range("2026-10-13", periods=14)

    def fc(sku, model, level, width):
        return pd.DataFrame(dict(store_id="S01", sku=sku, model=model, forecast_date=fdays, forecast_qty=level,
                                 lower=max(0, level - width / 2), upper=level + width / 2))
    forecasts = pd.concat([fc("SKU-HERO", "A", 0.4, 6.0), fc("SKU-HERO", "B", 7.7, 9.0),
                           fc("SKU-OK", "A", 5.0, 4.0), fc("SKU-OK", "B", 5.0, 4.0)], ignore_index=True)
    stock = pd.DataFrame(dict(store_id="S01", sku=["SKU-HERO", "SKU-OK"], on_hand=[0, 60]))
    products = pd.DataFrame(dict(sku=["SKU-HERO", "SKU-OK"], price_idr=[4500, 12000], shelf_life_days=[270, 365]))
    rates = pd.DataFrame(dict(category=["Cooking Essentials"], ask_rate_hat=[0.45]))
    return facts, forecasts, stock, products, rates


def rec():
    return build_recommendations(*inputs(), run_date=RUN).set_index("sku")


def test_one_row_per_series_with_the_table_columns():
    df = build_recommendations(*inputs(), run_date=RUN)
    assert list(df.columns) == COLUMNS and len(df) == 2 and set(df["run_date"]) == {RUN}


def test_hero_a_is_small_and_b_is_large_and_both_come_from_the_formula():
    h = rec().loc["SKU-HERO"]
    assert h.recommended_qty_a < 12 < 50 < h.recommended_qty_b
    assert h.forecast_a_7d == pytest.approx(2.8) and h.forecast_b_7d == pytest.approx(53.9)
    assert h.recommended_qty_b >= int(np.ceil(53.9))      # at least the forecast, plus safety stock, minus nothing on hand
    assert h.risk_type == "stockout_risk"


def test_overstock_means_hold_the_order():
    facts, fcs, stock, products, rates = inputs()
    products.loc[products.sku == "SKU-OK", "shelf_life_days"] = 5          # perishable: 5 days of cover is the limit
    fcs.loc[(fcs.sku == "SKU-OK"), ["forecast_qty", "lower", "upper"]] = [2.0, 1.0, 3.0]
    stock.loc[stock.sku == "SKU-OK", "on_hand"] = 15
    o = build_recommendations(facts, fcs, stock, products, rates, RUN).set_index("sku").loc["SKU-OK"]
    assert o.risk_type == "overstock" and o.recommended_qty_b == 0


def test_unmet_and_lost_revenue_use_the_estimated_ask_rate():
    h = rec().loc["SKU-HERO"]
    assert h.unmet_7d == 14 and h.lost_revenue_idr == round(14 / 0.45 * 4500)


def test_a_healthy_series_gets_no_flag_and_no_order_for_a_full_shelf():
    o = rec().loc["SKU-OK"]
    assert o.on_hand == 60 and pd.isna(o.risk_type) and o.recommended_qty_b == 0 and o.unmet_7d == 0


def test_series_without_an_ask_rate_have_zero_lost_revenue():
    facts, fcs, stock, products, rates = inputs()
    rates["ask_rate_hat"] = np.nan
    h = build_recommendations(facts, fcs, stock, products, rates, RUN).set_index("sku").loc["SKU-HERO"]
    assert h.lost_revenue_idr == 0 and h.unmet_7d == 14


# -- reason text ---------------------------------------------------------------------------------
def test_template_states_only_numbers_from_the_row():
    df = build_recommendations(*inputs(), run_date=RUN)
    row = df[df.sku == "SKU-HERO"].iloc[0].to_dict()
    f = facts_for(row, "Santan Kotak Kara 65 ml", {})
    text = template_reason(f)
    assert "Santan Kotak Kara 65 ml" in text and numbers_grounded(text, f)
    assert str(row["recommended_qty_b"]) in text and "POS-only forecast A" in text
    assert f["action"] == f"order {row['recommended_qty_b']} units" and "forecast_a_next_7_days" in f


def test_number_guard_rejects_invented_figures():
    f = {"on_hand": 0, "forecast_b_next_7_days": 53.9, "product": "X"}
    assert numbers_grounded("Order for the 53.9 units expected.", f)
    assert not numbers_grounded("Order 80 units, up 30%.", f)


def test_flagged_rows_get_text_and_the_llm_answer_is_used_only_when_grounded():
    df = build_recommendations(*inputs(), run_date=RUN)

    class Resp:
        def __init__(self, t): self.text = t

    class Client:
        def __init__(self, answer): self.answer, self.models = answer, self
        def generate_content(self, **kw): return Resp(self.answer)

    good, stats = add_reason_text(df, {"SKU-HERO": "Santan"}, {}, client=Client("Nothing on hand while 14 shoppers asked."), model="m")
    assert stats == {"gemini": 0, "template": 1}   # a text that never names the order quantity is not accepted
    qty = int(df.set_index("sku").loc["SKU-HERO", "recommended_qty_b"])
    good, stats = add_reason_text(df, {"SKU-HERO": "Santan"}, {}, client=Client(f"Nothing on hand while 14 shoppers asked: order {qty} units."), model="m")
    assert stats == {"gemini": 1, "template": 0}
    assert good.set_index("sku").loc["SKU-HERO", "reason_text"].startswith("Nothing on hand")
    prefixed, stats = add_reason_text(df, {"SKU-HERO": "Santan"}, {}, client=Client(f"Reason: order {qty} units now."), model="m")
    assert stats["gemini"] == 0
    assert good.set_index("sku").loc["SKU-OK", "reason_text"] is None   # unflagged rows get none
    bad, stats = add_reason_text(df, {"SKU-HERO": "Santan"}, {}, client=Client("Order 999 units now."), model="m")
    assert stats == {"gemini": 0, "template": 1} and "999" not in bad.set_index("sku").loc["SKU-HERO", "reason_text"]
    none, stats = add_reason_text(df, {}, {}, client=None)
    assert stats == {"gemini": 0, "template": 1}


def test_calendar_context_only_when_payday_starts_inside_the_order_cover():
    from app.forecast.pipeline import calendar_context

    assert calendar_context(dt.date(2026, 10, 13)) == {}                  # 25 Oct is 12 days away: not covered
    ctx = calendar_context(dt.date(2026, 10, 20))
    assert "starts in 5 days" in ctx["calendar"] and "2026-10-25" in ctx["calendar"]
    assert "calendar" in calendar_context(dt.date(2026, 10, 25)) and "starts in 0 days" in calendar_context(dt.date(2026, 10, 25))["calendar"]
