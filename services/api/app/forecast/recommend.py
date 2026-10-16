"""Recommendation rows for one run (build plan 7.5-7.7): quantities from A and B, one risk flag, a reason text."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import params
from .reorder import daily_sigma, recommended_qty, reorder_point, risk_type, window_sum

COLUMNS = ["run_date", "store_id", "sku", "on_hand", "forecast_a_7d", "forecast_b_7d", "unmet_7d",
           "recommended_qty_a", "recommended_qty_b", "risk_type", "lost_revenue_idr", "reason_text"]


def _series(fc: pd.DataFrame) -> dict[tuple[str, str, str], dict[str, list[float]]]:
    out: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    for (store, sku, model), g in fc.sort_values("forecast_date").groupby(["store_id", "sku", "model"]):
        out[(store, sku, model)] = {"q": g["forecast_qty"].tolist(), "lo": g["lower"].tolist(), "hi": g["upper"].tolist()}
    return out


def build_recommendations(facts: pd.DataFrame, forecasts: pd.DataFrame, stock: pd.DataFrame, products: pd.DataFrame,
                          ask_rates: pd.DataFrame, run_date: dt.date) -> pd.DataFrame:
    """One row per store and SKU.

    facts      daily history up to the day before run_date (date, store_id, sku, category, unmet_signals)
    forecasts  store_id, sku, model ('A'|'B'), forecast_date, forecast_qty, lower, upper
    stock      store_id, sku, on_hand (closing stock of the last data day)
    products   sku, price_idr, shelf_life_days
    ask_rates  category, ask_rate_hat (the estimate used to build forecast B)
    """
    last = facts["date"].max()
    recent = facts[facts["date"] > last - pd.Timedelta(days=7)]
    prev = facts[(facts["date"] <= last - pd.Timedelta(days=7)) & (facts["date"] > last - pd.Timedelta(days=14))]
    unmet7 = recent.groupby(["store_id", "sku"])["unmet_signals"].sum()
    unmet_prev = prev.groupby(["store_id", "sku"])["unmet_signals"].sum()
    rate = ask_rates.set_index("category")["ask_rate_hat"]
    price = products.set_index("sku")["price_idr"]
    shelf = products.set_index("sku")["shelf_life_days"]
    category = facts.drop_duplicates("sku").set_index("sku")["category"]
    fc = _series(forecasts)
    on_hand = stock.set_index(["store_id", "sku"])["on_hand"]
    cover, lead = params.COVER_DAYS, params.LEAD_TIME_DAYS

    rows = []
    for (store, sku), oh in on_hand.items():
        a, b = fc[(store, sku, "A")], fc[(store, sku, "B")]
        f7a, f7b = window_sum(a["q"], cover), window_sum(b["q"], cover)
        rec_a = recommended_qty(f7a, daily_sigma(a["lo"], a["hi"]), oh)
        rec_b = recommended_qty(f7b, daily_sigma(b["lo"], b["hi"]), oh)
        u7, up = float(unmet7.get((store, sku), 0.0)), float(unmet_prev.get((store, sku), 0.0))
        r = rate.get(category.get(sku))
        lost = (u7 / r) * price[sku] if (r and not np.isnan(r) and u7 > 0) else 0.0
        f_lead = window_sum(b["q"], lead)
        flag = risk_type(on_hand=oh, forecast_lead=f_lead, forecast_daily=f7b / cover,
                         perishable=bool(shelf[sku] <= params.PERISHABLE_SHELF_DAYS), unmet_7d=u7, unmet_prev_7d=up,
                         recommended_b=rec_b, reorder_pt=reorder_point(f_lead, daily_sigma(b["lo"], b["hi"]), lead))
        if flag == "overstock":
            rec_b = 0   # an overstock flag means "hold the order", so it must not carry a quantity
        rows.append({"run_date": run_date, "store_id": store, "sku": sku, "on_hand": int(oh),
                     "forecast_a_7d": round(f7a, 2), "forecast_b_7d": round(f7b, 2), "unmet_7d": int(u7),
                     "recommended_qty_a": int(rec_a), "recommended_qty_b": int(rec_b), "risk_type": flag,
                     "lost_revenue_idr": int(round(lost)), "reason_text": None})
    return pd.DataFrame(rows, columns=COLUMNS)
