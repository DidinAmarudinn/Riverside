"""Reorder quantity and risk flag (build plan 7.5-7.6), as plain functions.

    recommended = max(0, forecast(lead_time + review_period) + safety_stock - on_hand - on_order)
    safety_stock = z * sigma_day * sqrt(lead_time + review_period)

sigma_day comes from the model's own prediction interval, so a noisier series gets more safety stock.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from . import params


def window_sum(values: Sequence[float], days: int) -> float:
    """Forecast units over the first `days` days; a model can go slightly negative, demand cannot."""
    return float(sum(max(0.0, v) for v in list(values)[:days]))


def daily_sigma(lower: Sequence[float], upper: Sequence[float], days: int = params.COVER_DAYS) -> float:
    """Average daily standard deviation implied by the prediction interval over the first `days` days."""
    pairs = list(zip(lower, upper))[:days]
    if not pairs:
        return 0.0
    return float(sum(max(0.0, hi - lo) for lo, hi in pairs) / len(pairs) / (2 * params.INTERVAL_Z))


def safety_stock(sigma_day: float, days: int = params.COVER_DAYS, z: float = params.SERVICE_Z) -> float:
    return z * sigma_day * math.sqrt(days)


def recommended_qty(forecast_cover: float, sigma_day: float, on_hand: float, on_order: float = params.ON_ORDER,
                    days: int = params.COVER_DAYS) -> int:
    """Units to order now (whole units, rounded up)."""
    need = forecast_cover + safety_stock(sigma_day, days) - on_hand - on_order
    return max(0, math.ceil(need - 1e-9))


def reorder_point(forecast_lead: float, sigma_day: float, lead_days: int = params.LEAD_TIME_DAYS) -> float:
    """Classic reorder point: expected demand during the lead time plus safety stock for that time."""
    return forecast_lead + safety_stock(sigma_day, lead_days)


def risk_type(*, on_hand: float, forecast_lead: float, forecast_daily: float, perishable: bool, unmet_7d: float,
              unmet_prev_7d: float, recommended_b: int, reorder_pt: float) -> str | None:
    """One flag per SKU, in this order of precedence (judged on forecast B, the better estimate of demand):

    stockout_risk  on_hand is below the forecast for the lead time (it will run out before a delivery can arrive)
    unmet_spike    unmet signals in the last 7 days are at least SPIKE_MIN_SIGNALS and SPIKE_RATIO x the week before
    overstock      on_hand covers more than 14 days of forecast (5 for perishables), and is not a trivial stock
    reorder        none of the above, but on_hand is below the reorder point and the formula orders something
                   (stock that still covers the lead time plus its safety stock is left alone, even though the weekly
                   formula would top it up)
    """
    if on_hand < forecast_lead:
        return "stockout_risk"
    if unmet_7d >= params.SPIKE_MIN_SIGNALS and unmet_7d >= params.SPIKE_RATIO * max(unmet_prev_7d, 1):
        return "unmet_spike"
    days = params.OVERSTOCK_DAYS_PERISHABLE if perishable else params.OVERSTOCK_DAYS
    if on_hand >= params.OVERSTOCK_MIN_UNITS and on_hand > days * forecast_daily:
        return "overstock"
    if recommended_b > 0 and on_hand < reorder_pt:
        return "reorder"
    return None
