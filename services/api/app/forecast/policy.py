"""Re-simulate the replenishment policy over the backtest horizon with order quantities driven by a forecast.

The simulator's own policy orders up to an EMA of POS sales times cover days: it only ever sees POS. Here the same
world (same true demand, same supplier delays, same scripted supply failures) is replayed, identical up to the
backtest cutoff, and from then on each policy places its orders from a fixed 14-day forecast:

    order_t = max(0, ceil(forecast over the next cover days + safety stock - closing stock - on order))

so the only thing that differs between policies is the forecast they trust. Supply failures hit all of them alike.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import params
from .reorder import safety_stock


@dataclass
class Outcome:
    closing: np.ndarray      # (T, S, K) closing stock per test day
    sold: np.ndarray         # (T, S, K) units sold per test day
    demand: np.ndarray       # (T, S, K) true demand per test day

    @property
    def stockout_days(self) -> np.ndarray:
        """(S, K) number of test days that ended with an empty shelf."""
        return (self.closing == 0).sum(axis=0)

    @property
    def lost_units(self) -> np.ndarray:
        return (self.demand - self.sold).sum(axis=0)

    def excess_units(self, days: int = params.COVER_DAYS) -> np.ndarray:
        """(S, K) average over the test days of the stock above `days` days of average true demand."""
        cover = days * self.demand.mean(axis=0)
        return np.maximum(0.0, self.closing - cover[None]).mean(axis=0)


def _forecast_cover(forecast: np.ndarray, j: int, days: int) -> np.ndarray:
    """Forecast units for test days j+1 .. j+days; beyond the 14-day horizon the last week's mean is repeated."""
    horizon = forecast.shape[0]
    tail = forecast[max(0, horizon - 7):].mean(axis=0)
    total = np.zeros(forecast.shape[1:])
    for u in range(1, days + 1):
        total += forecast[j + u] if j + u < horizon else tail
    return total


def simulate(demand: np.ndarray, disruption: np.ndarray, wipe: np.ndarray, *, start: int, lead: int, cover: float,
             alpha: float, forecast: np.ndarray | None = None, sigma_day: np.ndarray | None = None,
             cover_days: int = params.COVER_DAYS) -> Outcome:
    """Replay the stock dynamics of data/sim/engine.simulate_stock; from day `start` on, orders follow `forecast`.

    demand, disruption, wipe: (D, S, K) arrays of the simulated world. `forecast`: (T, S, K) daily forecast for the
    days from `start` on (T = D - start); None keeps the simulator's own EMA policy for all days (a faithful replay).
    """
    D, S, K = demand.shape
    ema = demand[:7].mean(axis=0)
    on_hand = np.ceil(ema * cover)
    pipeline = np.zeros((D + lead + 1, S, K))
    closing_all, sold_all = np.zeros((D, S, K)), np.zeros((D, S, K))
    for d in range(D):
        recv = np.where(disruption[d], 0.0, pipeline[d])
        op = np.where(wipe[d], 0.0, on_hand + recv)
        sold = np.minimum(demand[d], op)
        clo = op - sold
        ema = alpha * sold + (1 - alpha) * ema
        on_order = pipeline[d + 1:].sum(axis=0)
        if forecast is None or d < start:
            order = np.maximum(0.0, np.ceil(ema * cover) - clo - on_order)
        else:
            j = d - start
            need = _forecast_cover(forecast, j, cover_days)
            if sigma_day is not None:
                need = need + safety_stock(sigma_day, cover_days)
            order = np.maximum(0.0, np.ceil(need) - clo - on_order)
        pipeline[d + lead] += order
        closing_all[d], sold_all[d], on_hand = clo, sold, clo
    sl = slice(start, D)
    return Outcome(closing=closing_all[sl], sold=sold_all[sl], demand=demand[sl])
