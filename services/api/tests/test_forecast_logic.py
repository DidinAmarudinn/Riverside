import math

import numpy as np
import pytest

from app.forecast import params
from app.forecast.metrics import bias, score, wape
from app.forecast.policy import Outcome, simulate
from app.forecast.reorder import daily_sigma, recommended_qty, risk_type, safety_stock, window_sum


# -- reorder formula -----------------------------------------------------------------------------
def test_window_sum_clips_negative_forecasts_and_stops_at_the_window():
    assert window_sum([2, -1, 3, 10], 3) == 5.0 and window_sum([1.5, 1.5], 7) == 3.0


def test_daily_sigma_comes_from_the_prediction_interval():
    assert daily_sigma([8] * 7, [8 + 2 * params.INTERVAL_Z * 3] * 7) == pytest.approx(3.0)
    assert daily_sigma([], []) == 0.0


def test_recommended_quantity_is_the_formula():
    sigma = 2.0
    ss = safety_stock(sigma)                       # z * sigma * sqrt(7)
    assert ss == pytest.approx(params.SERVICE_Z * sigma * math.sqrt(7))
    assert recommended_qty(50, sigma, on_hand=0) == math.ceil(50 + ss)
    assert recommended_qty(50, sigma, on_hand=10, on_order=5) == math.ceil(50 + ss - 15)
    assert recommended_qty(5, 0.0, on_hand=40) == 0   # never negative


def test_a_series_the_pos_forecast_thinks_is_dead_gets_no_order_but_b_does():
    # the heart of the project: POS shows zero sales on an empty shelf, forecast A sees no demand
    a = recommended_qty(window_sum([0.2] * 7, 7), daily_sigma([0] * 7, [0.5] * 7), on_hand=0)
    b = recommended_qty(window_sum([8.0] * 7, 7), daily_sigma([3] * 7, [13] * 7), on_hand=0)
    assert a <= 3 and b >= 56 and b > 15 * a


# -- risk flags ----------------------------------------------------------------------------------
BASE = dict(on_hand=40, forecast_lead=5, forecast_daily=5, perishable=False, unmet_7d=0, unmet_prev_7d=0, recommended_b=0,
            reorder_pt=12.0)


def flag(**kw):
    return risk_type(**{**BASE, **kw})


def test_stockout_risk_when_stock_is_below_the_lead_time_forecast():
    assert flag(on_hand=0, forecast_lead=8) == "stockout_risk"
    assert flag(on_hand=4, forecast_lead=5) == "stockout_risk"
    assert flag(on_hand=0, forecast_lead=0) is None  # nothing is expected to sell: not a risk


def test_unmet_spike_needs_enough_signals_and_a_jump():
    assert flag(unmet_7d=6, unmet_prev_7d=1) == "unmet_spike"
    assert flag(unmet_7d=6, unmet_prev_7d=4) is None          # busy before too: not a spike
    assert flag(unmet_7d=4, unmet_prev_7d=0) is None          # too few signals


def test_overstock_uses_a_shorter_window_for_perishables_and_ignores_tiny_stocks():
    assert flag(on_hand=80, forecast_daily=5) == "overstock"        # 16 days of cover > 14
    assert flag(on_hand=60, forecast_daily=5) is None               # 12 days
    assert flag(on_hand=30, forecast_daily=5, perishable=True) == "overstock"   # 6 days > 5
    assert flag(on_hand=6, forecast_daily=0.1) is None              # under OVERSTOCK_MIN_UNITS


def test_precedence_and_plain_reorder():
    assert flag(on_hand=0, forecast_lead=3, unmet_7d=9) == "stockout_risk"
    assert flag(unmet_7d=9, on_hand=200, forecast_daily=1) == "unmet_spike"
    assert flag(on_hand=9, recommended_b=12) == "reorder"      # below the reorder point (12) and the formula orders
    assert flag(on_hand=20, recommended_b=12) is None          # still above it: no flag, though the weekly formula tops up
    assert flag() is None


def test_reorder_point_is_lead_time_demand_plus_its_safety_stock():
    from app.forecast.reorder import reorder_point

    assert reorder_point(5, 2.0, lead_days=1) == pytest.approx(5 + params.SERVICE_Z * 2.0)


# -- metrics -------------------------------------------------------------------------------------
def test_wape_and_bias():
    assert wape([10, 10], [8, 14]) == pytest.approx(0.3) and bias([10, 10], [8, 14]) == pytest.approx(0.1)
    assert bias([10, 10], [5, 5]) == pytest.approx(-0.5)
    assert math.isnan(wape([0, 0], [1, 1]))


# -- policy simulation ---------------------------------------------------------------------------
def world(D=60, S=2, K=4, seed=0):
    rng = np.random.default_rng(seed)
    demand = rng.poisson(6, size=(D, S, K)).astype(np.int64)
    disruption = rng.random((D, S, K)) < 0.03
    wipe = np.zeros((D, S, K), dtype=bool)
    wipe[30, 0, 1] = True
    return demand, disruption, wipe


def test_replay_matches_the_simulators_own_policy_exactly():
    from sim.engine import simulate_stock

    demand, disruption, wipe = world()
    cfg = type("C", (), {"sim": {"stock": {"lead_time_days": 1, "cover_days": 4, "ema_alpha": 0.15}}})()
    _, _, closing, sales = simulate_stock(cfg, demand, disruption, wipe)
    out = simulate(demand, disruption, wipe, start=46, lead=1, cover=4, alpha=0.15)
    assert np.array_equal(out.closing, closing[46:]) and np.array_equal(out.sold, sales[46:])


def test_a_forecast_that_sees_the_demand_stocks_out_less_than_one_that_sees_none():
    demand, disruption, wipe = world(seed=2)
    disruption[:] = False
    wipe[:] = False
    start, T = 46, 14
    truth = demand[start:].astype(float)
    blind = np.zeros_like(truth)                  # forecast A on a series whose POS history was empty
    informed = np.full_like(truth, 6.0)           # forecast B recovered the true level
    a = simulate(demand, disruption, wipe, start=start, lead=1, cover=4, alpha=0.15, forecast=blind)
    b = simulate(demand, disruption, wipe, start=start, lead=1, cover=4, alpha=0.15, forecast=informed)
    assert b.stockout_days.sum() < a.stockout_days.sum() and b.lost_units.sum() < a.lost_units.sum()
    assert isinstance(b, Outcome) and b.closing.shape == (T, 2, 4)


def test_supply_failures_hit_every_policy_alike():
    demand, disruption, wipe = world(seed=4)
    disruption[40:, 0, 1] = True                  # receipts blocked for good on one series
    wipe[40, 0, 1] = True
    f = np.full((14, 2, 4), 6.0)
    a = simulate(demand, disruption, wipe, start=46, lead=1, cover=4, alpha=0.15, forecast=f * 0)
    b = simulate(demand, disruption, wipe, start=46, lead=1, cover=4, alpha=0.15, forecast=f)
    assert (a.stockout_days[0, 1], b.stockout_days[0, 1]) == (14, 14)


def test_excess_units_counts_only_stock_above_the_cover():
    closing = np.array([[[50.0]], [[10.0]]])
    demand = np.array([[[5.0]], [[5.0]]])
    o = Outcome(closing=closing, sold=demand, demand=demand)
    # cover = 7 days * 5 = 35; excess per day = 15 and 0; mean = 7.5
    assert o.excess_units()[0, 0] == pytest.approx(7.5)


def test_score_helper():
    import pandas as pd

    s = score(pd.DataFrame({"actual": [10, 10], "a": [10, 10], "b": [5, 5]}))
    assert s["a"]["wape"] == 0 and s["b"]["wape"] == pytest.approx(0.5)
