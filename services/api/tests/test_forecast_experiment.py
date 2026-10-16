import numpy as np
import pandas as pd

from app.forecast import experiment as ex


def test_verdict_depends_on_the_numbers_not_on_a_fixed_phrase():
    assert "B is closer on these 3 series" in ex.verdict({"mean": 0.2, "lo": 0.1, "hi": 0.3}, 3)
    assert "A is closer on these 9 series" in ex.verdict({"mean": -0.01, "lo": -0.05, "hi": 0.02}, 9)
    assert "cannot support a statistical claim" in ex.verdict({"mean": 0.5, "lo": 0.4, "hi": 0.6}, 3)
    assert ex.verdict({"mean": 0.02, "lo": 0.01, "hi": 0.03}, 600) == "B is better (the interval excludes zero)"
    assert ex.verdict({"mean": -0.02, "lo": -0.03, "hi": -0.01}, 600) == "A is better (the interval excludes zero)"
    assert "no clear difference" in ex.verdict({"mean": 0.0, "lo": -0.01, "hi": 0.01}, 600)


def test_compare_counts_wins_ties_and_resamples_series():
    w = type("W", (), {})()
    truth = np.full((7, 40, 1), 10.0)
    w.demand = np.concatenate([np.zeros((3, 40, 1)), truth])  # 3 training days, then the test window
    a, b = np.full((7, 40, 1), 10.0), np.full((7, 40, 1), 10.0)
    a[:, :10] = 2.0                       # A is badly wrong on 10 series, B is right everywhere
    e = {"cut": 3, "horizon": 7, "F": {"a": a, "b": b, "x": a}}
    r = ex.compare(w, e, np.ones((40, 1), bool))
    assert (r["b_closer"], r["a_closer"], r["tie"]) == (10, 0, 30)
    assert r["mean"] > 0 and r["lo"] > 0                 # every resample still favours B
    assert ex.compare(w, e, np.ones((40, 1), bool), b_key="x")["mean"] == 0


def test_naive_forecast_is_the_flat_mean_of_the_last_28_days():
    w = type("W", (), {})()
    w.sales = np.concatenate([np.full((10, 1, 1), 99.0), np.full((28, 1, 1), 4.0)])
    f = ex.naive_forecast(w, cut=38, horizon=5)
    assert f.shape == (5, 1, 1) and (f == 4.0).all()


def test_to_array_places_values_by_date_store_and_sku():
    df = pd.DataFrame(dict(date=["2026-10-01", "2026-10-02"], store_id=["S1", "S2"], sku=["A", "B"], v=[3.0, 5.0]))
    out = ex.to_array(df, "v", pd.date_range("2026-10-01", periods=2), ["S1", "S2"], ["A", "B"])
    assert out[0, 0, 0] == 3.0 and out[1, 1, 1] == 5.0 and out.sum() == 8.0


def test_report_renders_from_synthetic_results():
    acc = {n: {"n_series": 5, "actual_units": 50.0, **{v: {"wape": 0.5, "bias": -0.1} for v in [*ex.VARIANTS, "naive"]}}
           for n in ("all series", "out of stock on the cutoff day", "hero (S01, SKU-0001)")}
    cmp_ = {n: {"mean": 0.01, "lo": -0.01, "hi": 0.03, "b_closer": 2, "a_closer": 1, "tie": 2} for n in acc}
    pol = {n: {k: {"stockout_days": 1, "lost_units": 2.0, "excess_units": 3.0} for k in ["status_quo", *ex.VARIANTS]} for n in acc}
    sens = {g: {v: {"mean": 0.0, "lo": -0.1, "hi": 0.1} for v in ("b", "b_rate_x0_5", "b_rate_x1_5")}
            for g in ("out of stock on the cutoff day", "stockout in the last 14 training days")}
    for r in acc.values():
        pass
    acc["stockout in the last 14 training days"] = dict(next(iter(acc.values())))
    res = {k: {"spec": ex.EXPERIMENTS[k], "acc": acc, "cmp": cmp_, "pol": pol, "sens": sens, "train_range": "a to b", "test_range": "c to d"}
           for k in ("main", "stress")}
    rates = pd.DataFrame(dict(category=["Snacks", "ALL"], ask_rate_hat=[0.4, 0.4], signals=[5.0, 5.0], expected_unmet=[12.0, 12.0],
                              source=["category", "pooled"]))
    hero = dict(on_hand=0, forecast_a_7d=2.6, forecast_b_7d=52.0, unmet_7d=17, recommended_qty_a=10, recommended_qty_b=64)
    meta = dict(date="2026-10-16", n_series=642, pooled_bt=0.7, pooled_late=0.5, pooled_prod=0.47, limits=["one limit"])
    text = ex.render(res, rates, 0.35, hero, meta)
    assert text.startswith("# Experiment results") and "orders 10" in text
    assert "validation only" in text and "0.35" in text and "one limit" in text
    assert text.count("## ") >= 6
