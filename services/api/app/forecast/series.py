"""Forecast A and B training series, and the ask-rate estimate behind B (build plan 7.1-7.2).

A  = POS units sold per day.
B  = A plus, on stockout days, the unmet demand implied by the kiosk signals:
     y_b = qty_sold + unmet_signals / ask_rate_hat

`ask_rate_hat` is the share of unmet shoppers who show up as a kiosk signal. It is **estimated from the training
data**, never read from the simulator: for every stockout day the demand we would expect comes from in-stock days
around it (same weekday, +-28 days); the part of that demand that POS did not serve is the expected unmet demand,
and ask_rate_hat = total unmet signals / total expected unmet demand, per category, falling back to the pooled
estimate when a category has too little evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import params

FACT_COLUMNS = ["date", "store_id", "sku", "category", "qty_sold", "is_stockout", "unmet_signals"]


def expected_demand(facts: pd.DataFrame, window_days: int = params.ASK_WINDOW_DAYS) -> pd.Series:
    """Expected daily demand on each stockout row (NaN on in-stock rows).

    Mean units sold on in-stock days of the same store+SKU, same weekday, within +-window_days; when there is no such
    day, the mean over all in-stock days of the series; NaN when the series was never in stock.
    """
    out = pd.Series(np.nan, index=facts.index, dtype=float)
    for _, g in facts.groupby(["store_id", "sku"], sort=False):
        stock = g["is_stockout"].to_numpy(bool)
        if not stock.any():
            continue
        day = g["date"].to_numpy("datetime64[D]").astype("int64")
        dow = (day + 3) % 7                      # weekday of the epoch day count (1970-01-01 was a Thursday)
        sold = g["qty_sold"].to_numpy(float)
        in_stock = ~stock
        series_mean = sold[in_stock].mean() if in_stock.any() else np.nan
        for i in np.flatnonzero(stock):
            near = in_stock & (dow == dow[i]) & (np.abs(day - day[i]) <= window_days)
            out.loc[g.index[i]] = sold[near].mean() if near.any() else series_mean
    return out


def estimate_ask_rates(facts: pd.DataFrame) -> pd.DataFrame:
    """Per category: ask_rate_hat with the evidence it rests on.

    Columns: category, ask_rate_hat, signals, expected_unmet, source ('category' | 'pooled' | 'none').
    """
    f = facts.copy()
    f["expected"] = expected_demand(f)
    stock = f[f["is_stockout"].astype(bool) & f["expected"].notna()].copy()
    stock["expected_unmet"] = (stock["expected"] - stock["qty_sold"]).clip(lower=0)
    per_cat = stock.groupby("category").agg(signals=("unmet_signals", "sum"), expected_unmet=("expected_unmet", "sum"))
    pooled_signals, pooled_unmet = per_cat["signals"].sum(), per_cat["expected_unmet"].sum()

    def usable(signals: float, unmet: float) -> bool:
        return unmet >= params.ASK_MIN_EXPECTED_UNITS and signals >= params.ASK_MIN_SIGNALS

    pooled = (min(max(pooled_signals / pooled_unmet, params.ASK_FLOOR), params.ASK_CEIL)
              if usable(pooled_signals, pooled_unmet) else np.nan)
    rows = []
    for cat in sorted(f["category"].dropna().unique()):
        s, u = (per_cat.loc[cat, "signals"], per_cat.loc[cat, "expected_unmet"]) if cat in per_cat.index else (0.0, 0.0)
        if usable(s, u):
            rate, source = min(max(s / u, params.ASK_FLOOR), params.ASK_CEIL), "category"
        elif not np.isnan(pooled):
            rate, source = pooled, "pooled"
        else:
            rate, source = np.nan, "none"
        rows.append({"category": cat, "ask_rate_hat": rate, "signals": float(s), "expected_unmet": float(u),
                     "source": source})
    pooled_row = {"category": "ALL", "ask_rate_hat": pooled, "signals": float(pooled_signals),
                  "expected_unmet": float(pooled_unmet), "source": "pooled" if not np.isnan(pooled) else "none"}
    return pd.DataFrame(rows + [pooled_row])


def build_series(facts: pd.DataFrame, ask_rates: pd.DataFrame, factor: float = 1.0) -> pd.DataFrame:
    """Daily training series for one cutoff: y_a (POS) and y_b (POS + unmet / ask_rate_hat * factor).

    `factor` scales the ask rate for the sensitivity runs (0.5 = half as many unmet shoppers are seen, so more unmet
    demand is inferred). A category without an estimate gets y_b = y_a.
    """
    rate = ask_rates.set_index("category")["ask_rate_hat"]
    f = facts.copy()
    f["ask_rate_hat"] = f["category"].map(rate)
    f["unmet_est"] = 0.0
    on = f["is_stockout"].astype(bool) & f["ask_rate_hat"].notna() & (f["unmet_signals"] > 0)
    f.loc[on, "unmet_est"] = f.loc[on, "unmet_signals"] / (f.loc[on, "ask_rate_hat"] * factor)
    f["y_a"] = f["qty_sold"].astype(float)
    f["y_b"] = f["y_a"] + f["unmet_est"]
    return f
