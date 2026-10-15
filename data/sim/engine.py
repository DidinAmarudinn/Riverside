"""Core simulator: true_demand -> stock -> pos_sales (censored).

POS = min(demand, stock available). That `min` is where censoring happens, and the
whole point of the project is recovering what the `min` hid.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import SimConfig, load_config, load_master, load_sku_params


@dataclass
class World:
    cfg: SimConfig
    master: pd.DataFrame
    dates: pd.DatetimeIndex
    store_ids: list[str]
    skus: list[str]
    demand: np.ndarray        # (D, S, K) true demand, units
    opening: np.ndarray       # stock available at the start of the day (after receipts)
    received: np.ndarray
    closing: np.ndarray
    sales: np.ndarray         # POS units = min(demand, opening)
    disruption: np.ndarray    # bool: receipts blocked that day
    wipe: np.ndarray          # bool: stock wiped at start of day (supply failure)
    resolved_scenarios: list[dict] = field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.demand.shape

    def sku_index(self, sku: str) -> int:
        return self.skus.index(sku)

    def store_index(self, store_id: str) -> int:
        return self.store_ids.index(store_id)


# --------------------------------------------------------------------------- demand

def _payday_factor(cfg: SimConfig) -> np.ndarray:
    """Per-day base uplift (before category sensitivity), shape (D,)."""
    sim = cfg.sim
    uplift = {int(k): float(v) for k, v in sim["payday_uplift"].items()}
    dip = float(sim["midmonth_dip"])
    out = np.zeros(len(cfg.dates))
    for i, d in enumerate(cfg.dates):
        if d.day in uplift:
            out[i] = uplift[d.day]
        elif 10 <= d.day <= 18:
            out[i] = -dip
    return out


def _event_factor(cfg: SimConfig, master: pd.DataFrame) -> np.ndarray:
    """(D, K) multiplicative event factor."""
    D, K = len(cfg.dates), len(master)
    out = np.ones((D, K))
    cats = master["category"].to_numpy()
    for ev in cfg.sim.get("events", []):
        start, end = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
        day_mask = (cfg.dates >= start) & (cfg.dates <= end)
        sku_mask = np.isin(cats, ev["categories"])
        out[np.ix_(day_mask, sku_mask)] *= float(ev["multiplier"])
    return out


def build_demand(cfg: SimConfig, master: pd.DataFrame, params: pd.DataFrame,
                 rng: np.random.Generator) -> np.ndarray:
    sim = cfg.sim
    dates = cfg.dates
    D, S, K = len(dates), len(cfg.stores), len(master)

    base_units = master[["sku"]].merge(params, on="sku", how="left")["base_units"].to_numpy()
    size = np.array([s["size_factor"] for s in cfg.stores])
    affinity = rng.lognormal(mean=0.0, sigma=0.25, size=(S, K))
    base = base_units[None, :] * size[:, None] * affinity            # (S, K)

    # Scenario overrides: exact base rate for a given store/product.
    name_to_idx = {n: i for i, n in enumerate(master["name"])}
    store_to_idx = {s["id"]: i for i, s in enumerate(cfg.stores)}
    for sc in cfg.scenarios:
        if "base_units_override" in sc:
            base[store_to_idx[sc["store_id"]], name_to_idx[sc["product"]]] = float(sc["base_units_override"])

    weekday = np.array(sim["weekday_factors"])[dates.dayofweek]       # (D,)
    sens = master["category"].map(sim.get("payday_sensitivity", {})).fillna(1.0).to_numpy()  # (K,)
    pay = 1.0 + _payday_factor(cfg)[:, None] * sens[None, :]          # (D, K)
    event = _event_factor(cfg, master)                                # (D, K)
    trend_slope = rng.normal(0.0, 0.10, size=K)                       # +-10% over the window
    trend = 1.0 + trend_slope[None, :] * (np.arange(D)[:, None] / D)  # (D, K)

    lam = (base[None, :, :]
           * weekday[:, None, None]
           * (pay * event * trend)[:, None, :])                       # (D, S, K)
    noise = rng.gamma(shape=sim["demand_noise_shape"], scale=1.0 / sim["demand_noise_shape"], size=lam.shape)
    return rng.poisson(lam * noise).astype(np.int64)


# --------------------------------------------------------------------------- stock

def build_disruptions(cfg: SimConfig, master: pd.DataFrame, rng: np.random.Generator
                      ) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Random supplier delays + scripted supply failures. Returns (disruption, wipe, resolved)."""
    D, S, K = len(cfg.dates), len(cfg.stores), len(master)
    stock_cfg = cfg.sim["stock"]
    disruption = np.zeros((D, S, K), dtype=bool)
    wipe = np.zeros((D, S, K), dtype=bool)

    lo, hi = stock_cfg["random_disruption_days"]
    starts = np.argwhere(rng.random((D, S, K)) < stock_cfg["random_disruption_prob"])
    lengths = rng.integers(lo, hi + 1, size=len(starts))
    for (d, s, k), n in zip(starts, lengths):
        disruption[d:d + n, s, k] = True

    name_to_idx = {n: i for i, n in enumerate(master["name"])}
    store_to_idx = {s["id"]: i for i, s in enumerate(cfg.stores)}
    resolved = []
    for sc in cfg.scenarios:
        if sc["type"] != "supply_failure":
            continue
        k, s = name_to_idx[sc["product"]], store_to_idx[sc["store_id"]]
        end = D - int(sc["ends_days_before_end"])
        start = end - int(sc["days"])
        disruption[start:end, s, k] = True
        wipe[start, s, k] = True
        resolved.append({
            **sc,
            "sku": master["sku"].iloc[k],
            "start_date": str(cfg.dates[start].date()),
            "end_date": str(cfg.dates[end - 1].date()),
        })
    return disruption, wipe, resolved


def simulate_stock(cfg: SimConfig, demand: np.ndarray, disruption: np.ndarray, wipe: np.ndarray):
    """Naive POS-driven replenishment: order-up-to (EMA of POS * cover days)."""
    st = cfg.sim["stock"]
    lead, cover, alpha = int(st["lead_time_days"]), float(st["cover_days"]), float(st["ema_alpha"])
    D, S, K = demand.shape

    ema = demand[:7].mean(axis=0)                       # warm start
    on_hand = np.ceil(ema * cover)
    pipeline = np.zeros((D + lead + 1, S, K))
    opening = np.zeros((D, S, K))
    received = np.zeros((D, S, K))
    closing = np.zeros((D, S, K))
    sales = np.zeros((D, S, K))

    for d in range(D):
        recv = np.where(disruption[d], 0.0, pipeline[d])
        op = np.where(wipe[d], 0.0, on_hand + recv)
        sold = np.minimum(demand[d], op)
        clo = op - sold
        ema = alpha * sold + (1 - alpha) * ema          # <- forecast sees POS only
        on_order = pipeline[d + 1:].sum(axis=0)
        order = np.maximum(0.0, np.ceil(ema * cover) - clo - on_order)
        pipeline[d + lead] += order
        opening[d], received[d], closing[d], sales[d] = op, recv, clo, sold
        on_hand = clo
    return opening.astype(int), received.astype(int), closing.astype(int), sales.astype(int)


# --------------------------------------------------------------------------- assemble

def build_world(cfg: SimConfig | None = None) -> World:
    cfg = cfg or load_config()
    params = load_sku_params()
    # The simulator only ever acts on carried SKUs; NC rows exist for the catalog/gaps, not for demand.
    master = (load_master().query("is_carried").reset_index(drop=True)
              .merge(params[["sku", "subcategory", "perishable"]], on="sku", how="left"))
    rng = np.random.default_rng(int(cfg.sim["seed"]))

    demand = build_demand(cfg, master, params, rng)
    disruption, wipe, resolved = build_disruptions(cfg, master, rng)
    opening, received, closing, sales = simulate_stock(cfg, demand, disruption, wipe)
    return World(
        cfg=cfg, master=master, dates=cfg.dates,
        store_ids=[s["id"] for s in cfg.stores], skus=master["sku"].tolist(),
        demand=demand, opening=opening, received=received, closing=closing, sales=sales,
        disruption=disruption, wipe=wipe, resolved_scenarios=resolved,
    )


def _frame(world: World, **arrays: np.ndarray) -> pd.DataFrame:
    D, S, K = world.shape
    idx = pd.MultiIndex.from_product([world.dates.strftime("%Y-%m-%d"), world.store_ids, world.skus],
                                     names=["date", "store_id", "sku"])
    return pd.DataFrame({k: v.reshape(-1) for k, v in arrays.items()}, index=idx).reset_index()


def to_frames(world: World) -> dict[str, pd.DataFrame]:
    price = world.master["price_idr"].to_numpy()
    return {
        # Contract column names: docs/api-contract.md §1 / sql/01_tables.sql.
        "true_demand": _frame(world, demand_qty=world.demand),
        "stock_events": _frame(
            world,
            opening_stock=world.opening, received_qty=world.received,
            closing_stock=world.closing, is_stockout=(world.closing == 0).astype(int),
        ),
        "pos_sales": _frame(
            world, qty_sold=world.sales,
            revenue_idr=(world.sales * price[None, None, :]).astype(np.int64),
        ),
    }


# --------------------------------------------------------------------------- calendar & stores

def _in_range(day: pd.Timestamp, window: dict | None) -> bool:
    if not window or "start" not in window or "end" not in window:
        return False
    return pd.Timestamp(window["start"]) <= day <= pd.Timestamp(window["end"])


def build_calendar(cfg: SimConfig) -> pd.DataFrame:
    """calendar_context per contract: payday window (25-5), holidays, ramadan/lebaran, weather.

    Ramadan/Lebaran fall outside the Jul-Oct simulation window, so those flags are normally all
    false; they stay configurable so the window can be moved without touching code.
    """
    sim = cfg.sim
    rng = np.random.default_rng(int(sim["seed"]) + 7)
    holidays = {str(h["date"]): str(h["name"]) for h in sim.get("holidays", [])}
    ramadan, lebaran = sim.get("ramadan"), sim.get("lebaran_window")
    weather = sim.get("weather", {"sunny": 0.5, "cloudy": 0.3, "rain": 0.2})
    labels, probs = list(weather), np.array(list(weather.values()), dtype=float)
    probs = probs / probs.sum()

    rows = []
    for d in cfg.dates:
        ds = d.strftime("%Y-%m-%d")
        rows.append({
            "date": ds,
            "is_payday_window": bool(d.day >= 25 or d.day <= 5),
            "is_holiday": ds in holidays,
            "holiday_name": holidays.get(ds, ""),
            "is_ramadan": _in_range(d, ramadan),
            "is_lebaran_window": _in_range(d, lebaran),
            "weather": str(rng.choice(labels, p=probs)),
        })
    return pd.DataFrame(rows)


def build_stores(cfg: SimConfig) -> pd.DataFrame:
    """stores per contract: store_id, name, city, lat, lng (from seed_scenarios.yaml)."""
    return pd.DataFrame([{
        "store_id": s["id"], "name": s["name"],
        "city": s.get("city", ""), "lat": s.get("lat"), "lng": s.get("lng"),
    } for s in cfg.stores])
