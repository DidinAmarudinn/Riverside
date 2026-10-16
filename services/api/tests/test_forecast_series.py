import numpy as np
import pandas as pd

from app.forecast import params
from app.forecast.series import build_series, estimate_ask_rates, expected_demand


def world(true_rate=0.3, days=84, seed=1, categories=("Snacks",), stock_blocks=((20, 6), (45, 8), (65, 5))):
    """Many series with flat demand of ~10 a day; each goes out of stock in a few blocks, and every unmet unit
    becomes a kiosk signal with probability `true_rate`."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-07-15")
    rows = []
    for ci, cat in enumerate(categories):
        for k in range(30):
            for d in range(days):
                demand = rng.poisson(10)
                out = any(s <= d < s + n for s, n in stock_blocks)
                sold = 0 if out else demand
                unmet = demand if out else 0
                rows.append(dict(date=start + pd.Timedelta(days=d), store_id="S01", sku=f"{cat}-{k}", category=cat,
                                 qty_sold=sold, is_stockout=out, unmet_signals=int(rng.binomial(unmet, true_rate))))
    return pd.DataFrame(rows)


def test_expected_demand_uses_same_weekday_in_stock_days_only():
    days = pd.date_range("2026-07-15", periods=70)
    f = pd.DataFrame(dict(date=days, store_id="S", sku="X", category="C", qty_sold=0, is_stockout=False,
                          unmet_signals=0))
    f["qty_sold"] = [20 if d.dayofweek == 4 else 5 for d in days]  # Fridays sell 20, other days 5
    f.loc[f["date"] == pd.Timestamp("2026-08-14"), ["qty_sold", "is_stockout"]] = [0, True]  # a Friday, empty shelf
    exp = expected_demand(f)
    assert exp.dropna().tolist() == [20.0]  # the Fridays around it, not the overall mean (~7)
    assert exp[f["is_stockout"]].index.tolist() == f.index[f["is_stockout"]].tolist()


def test_expected_demand_falls_back_to_the_series_mean_then_nan():
    days = pd.date_range("2026-07-15", periods=10)
    f = pd.DataFrame(dict(date=days, store_id="S", sku="X", category="C", qty_sold=[4] * 9 + [0],
                          is_stockout=[False] * 9 + [True], unmet_signals=0))
    assert expected_demand(f).dropna().tolist() == [4.0]  # no other day shares that weekday within the data span
    f["is_stockout"] = True
    assert expected_demand(f).isna().all()  # never in stock: nothing to learn from


def test_ask_rate_is_recovered_from_the_data_without_being_told():
    for true_rate in (0.2, 0.35, 0.6):
        est = estimate_ask_rates(world(true_rate)).set_index("category")
        assert est.loc["Snacks", "source"] == "category"
        assert abs(est.loc["Snacks", "ask_rate_hat"] - true_rate) < 0.06, (true_rate, est.loc["Snacks"])


def test_a_category_with_little_evidence_uses_the_pooled_estimate():
    f = pd.concat([world(0.4, categories=("Snacks",)),
                   world(0.4, categories=("Tiny",), stock_blocks=((30, 1),)).query("sku == 'Tiny-0'")])
    est = estimate_ask_rates(f).set_index("category")
    assert est.loc["Tiny", "source"] == "pooled" and est.loc["Tiny", "ask_rate_hat"] == est.loc["ALL", "ask_rate_hat"]


def test_no_stockouts_means_no_estimate_and_b_equals_a():
    f = world(stock_blocks=())
    est = estimate_ask_rates(f)
    assert est["ask_rate_hat"].isna().all() and (est["source"] == "none").all()
    s = build_series(f, est)
    assert (s["y_b"] == s["y_a"]).all()


def test_b_adds_unmet_demand_only_on_stockout_days():
    f = world(0.3)
    est = estimate_ask_rates(f)
    s = build_series(f, est)
    ins, outs = s[~s["is_stockout"]], s[s["is_stockout"]]
    assert (ins["y_b"] == ins["y_a"]).all()
    assert (outs["y_b"] >= outs["y_a"]).all() and outs["y_b"].sum() > outs["y_a"].sum()
    rate = est.set_index("category").loc["Snacks", "ask_rate_hat"]
    row = outs[outs["unmet_signals"] > 0].iloc[0]
    assert abs(row["y_b"] - (row["qty_sold"] + row["unmet_signals"] / rate)) < 1e-9


def test_b_reconstructs_most_of_the_lost_demand():
    f = world(0.35, seed=3)
    s = build_series(f, estimate_ask_rates(f))
    lost_true = 10.0 * s["is_stockout"].sum()            # demand of ~10 a day was censored on those days
    assert abs(s["y_b"].sum() - s["y_a"].sum() - lost_true) / lost_true < 0.15


def test_sensitivity_factor_scales_the_inferred_unmet_demand():
    f = world(0.3)
    est = estimate_ask_rates(f)
    base = build_series(f, est)
    half, one_half = build_series(f, est, 0.5), build_series(f, est, 1.5)
    extra = lambda s: (s["y_b"] - s["y_a"]).sum()  # noqa: E731
    assert abs(extra(half) - 2 * extra(base)) < 1e-6 and abs(extra(one_half) - extra(base) / 1.5) < 1e-6
    assert params.SENSITIVITY_FACTORS == {"b_rate_x0_5": 0.5, "b_rate_x1_5": 1.5}
