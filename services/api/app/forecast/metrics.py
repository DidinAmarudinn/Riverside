"""Forecast error metrics for the backtest (build plan 7.8)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def wape(actual, forecast) -> float:
    """Weighted absolute percentage error: sum|actual - forecast| / sum(actual). NaN when nothing was demanded."""
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    total = a.sum()
    return float(np.abs(a - f).sum() / total) if total > 0 else float("nan")


def bias(actual, forecast) -> float:
    """Signed error as a share of demand: negative means the forecast is too low."""
    a, f = np.asarray(actual, float), np.asarray(forecast, float)
    total = a.sum()
    return float((f - a).sum() / total) if total > 0 else float("nan")


def score(df: pd.DataFrame, actual: str = "actual", columns: tuple[str, ...] = ("a", "b")) -> dict[str, dict[str, float]]:
    """WAPE and bias of each forecast column against `actual`, over all rows of `df`."""
    return {c: {"wape": wape(df[actual], df[c]), "bias": bias(df[actual], df[c])} for c in columns}
