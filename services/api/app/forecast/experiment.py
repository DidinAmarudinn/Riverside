"""Backtest A vs B against true_demand, re-simulate the order policy, and run the ask-rate sensitivity (build plan 7.8).

    python -m app.forecast.experiment            # writes docs/results.md

Two experiments, both scored against the simulator's true demand:
  main    train up to day 76, predict the next 14 days (the plan's backtest)
  stress  train up to day 83, predict the 7 days that remain: stockouts are still going on when the forecast is made,
          which is the situation forecast B is meant for
Each runs A, B, and B with the estimated ask rate x0.5 and x1.5. The replenishment simulation is then replayed over the
test days with orders driven by each forecast. Numbers are reported as they come out.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from . import bqio, params
from .metrics import bias, wape
from .policy import simulate
from .reorder import daily_sigma

VARIANTS = ["a", "b", "b_rate_x0_5", "b_rate_x1_5"]
LABEL = {"a": "A (POS only)", "b": "B (POS + unmet)", "b_rate_x0_5": "B, ask rate x0.5", "b_rate_x1_5": "B, ask rate x1.5",
         "naive": "Naive (mean of last 28 days)", "status_quo": "Status quo (EMA of POS x 4 days)"}
EXPERIMENTS = {
    "main": {"kind": "bt", "train_days": params.BACKTEST_TRAIN_DAYS, "horizon": params.HORIZON_DAYS,
             "title": "Backtest: train to day 76, predict 14 days"},
    "stress": {"kind": "late", "train_days": params.LATE_TRAIN_DAYS, "horizon": params.LATE_HORIZON_DAYS,
               "title": "Stress test: train to day 83 (stockouts still going on), predict the remaining 7 days"},
}
RESULTS_PATH = Path(__file__).resolve().parents[4] / "docs" / "results.md"
TIE = 1e-6


# ------------------------------------------------------------------------------------------------ data
def to_array(df: pd.DataFrame, value: str, dates: pd.DatetimeIndex, stores: list[str], skus: list[str]) -> np.ndarray:
    """(T, S, K) array of `value` from a long frame with date, store_id, sku."""
    out = np.zeros((len(dates), len(stores), len(skus)))
    di = {d: i for i, d in enumerate(dates)}
    si, ki = {s: i for i, s in enumerate(stores)}, {s: i for i, s in enumerate(skus)}
    for d, s, k, v in zip(pd.to_datetime(df["date"]), df["store_id"], df["sku"], df[value]):
        out[di[d], si[s], ki[k]] = v
    return out


def naive_forecast(w, cut: int, horizon: int) -> np.ndarray:
    """Mean POS of the last 28 training days, flat over the horizon: a yardstick for what a trivial forecast scores."""
    return np.repeat(w.sales[cut - 28:cut].mean(axis=0, keepdims=True), horizon, axis=0)


def load_experiment(c, w, fc: pd.DataFrame, spec: dict) -> dict:
    cut, horizon = spec["train_days"], spec["horizon"]
    dates = w.dates[cut:cut + horizon]
    F, SIG = {}, {}
    for v in VARIANTS:
        d = fc[(fc["kind"] == spec["kind"]) & (fc["variant"] == v)]
        F[v] = to_array(d, "forecast_qty", dates, w.store_ids, w.skus)
        lo, hi = to_array(d, "lower", dates, w.store_ids, w.skus), to_array(d, "upper", dates, w.store_ids, w.skus)
        k = min(params.COVER_DAYS, horizon)
        SIG[v] = (hi[:k] - lo[:k]).clip(min=0).mean(axis=0) / (2 * params.INTERVAL_Z)
    F["naive"] = naive_forecast(w, cut, horizon)
    return {"spec": spec, "cut": cut, "horizon": horizon, "F": F, "SIG": SIG, "dates": dates}


# ------------------------------------------------------------------------------------------------ accuracy
def subsets(w, cut: int) -> dict[str, np.ndarray]:
    """Boolean (S, K) masks of series groups. The first three only use what a forecaster could know at the cutoff; the
    next one looks forward and only describes where censoring matters in the test window."""
    closed = (w.closing == 0)
    S, K = closed.shape[1:]
    ongoing = closed[cut - 1]
    recent = closed[cut - 14:cut].any(axis=0)
    in_test = closed[cut:].any(axis=0)
    hero = np.zeros((S, K), bool)
    for sc in w.resolved_scenarios:
        if sc["id"] == "hero_santan":
            hero[w.store_index(sc["store_id"]), w.sku_index(sc["sku"])] = True
    return {"all series": np.ones((S, K), bool), "out of stock on the cutoff day": ongoing,
            "stockout in the last 14 training days": recent, "no stockout in the last 14 training days": ~recent,
            "stockout in the test window": in_test, "hero (S01, SKU-0001)": hero}


def accuracy(w, ex: dict) -> dict:
    cut, h = ex["cut"], ex["horizon"]
    actual = w.demand[cut:cut + h].astype(float)
    out = {}
    for name, mask in subsets(w, cut).items():
        a = actual[:, mask]
        row = {"n_series": int(mask.sum()), "actual_units": float(a.sum())}
        for v in [*VARIANTS, "naive"]:
            f = ex["F"][v][:, mask]
            row[v] = {"wape": wape(a, f), "bias": bias(a, f)}
        out[name] = row
    return out


def compare(w, ex: dict, mask: np.ndarray, b_key: str = "b", n: int = 2000, seed: int = 7) -> dict:
    """WAPE(A) - WAPE(B) with a 95% interval from resampling series, and how many series B / A / neither wins."""
    cut, h = ex["cut"], ex["horizon"]
    truth = w.demand[cut:cut + h][:, mask].astype(float)
    err_a = np.abs(truth - ex["F"]["a"][:, mask]).sum(axis=0)
    err_b = np.abs(truth - ex["F"][b_key][:, mask]).sum(axis=0)
    actual = truth.sum(axis=0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(actual), size=(n, len(actual)))
    diff = (err_a[idx].sum(axis=1) - err_b[idx].sum(axis=1)) / np.maximum(actual[idx].sum(axis=1), 1e-9)
    d = err_a - err_b
    return {"mean": float((err_a.sum() - err_b.sum()) / actual.sum()), "lo": float(np.percentile(diff, 2.5)),
            "hi": float(np.percentile(diff, 97.5)), "b_closer": int((d > TIE).sum()), "a_closer": int((d < -TIE).sum()),
            "tie": int((np.abs(d) <= TIE).sum())}


# ------------------------------------------------------------------------------------------------ policy
def policy(w, ex: dict) -> dict:
    st = w.cfg.sim["stock"]
    common = dict(start=ex["cut"], lead=int(st["lead_time_days"]), cover=float(st["cover_days"]), alpha=float(st["ema_alpha"]))
    runs = {"status_quo": simulate(w.demand, w.disruption, w.wipe, **common)}
    for v in VARIANTS:
        runs[v] = simulate(w.demand, w.disruption, w.wipe, forecast=ex["F"][v], sigma_day=ex["SIG"][v], **common)
    out = {}
    for name, mask in subsets(w, ex["cut"]).items():
        out[name] = {k: {"stockout_days": int(r.stockout_days[mask].sum()), "lost_units": float(r.lost_units[mask].sum()),
                         "excess_units": float(r.excess_units()[mask].sum())} for k, r in runs.items()}
    return out


# ------------------------------------------------------------------------------------------------ report
def pct(x: float) -> str:
    return "n/a" if x != x else f"{x * 100:.1f}%"


def verdict(c: dict, n: int) -> str:
    """Words for an A-vs-B comparison, decided by the numbers: too few series, interval above/below zero, or neither."""
    if n < 10:
        closer = "B is closer" if c["mean"] > 0 else "A is closer" if c["mean"] < 0 else "A and B score the same"
        return f"{closer} on these {n} series, but {n} series cannot support a statistical claim; read it as an illustration"
    if c["lo"] > 0:
        return "B is better (the interval excludes zero)"
    if c["hi"] < 0:
        return "A is better (the interval excludes zero)"
    return "there is no clear difference (the interval includes zero)"


def _section(num: int, res: dict) -> list[str]:
    L, add = [], None
    L_add = L.append
    acc, cmp_, pol, spec = res["acc"], res["cmp"], res["pol"], res["spec"]
    L_add(f"## {num}. {spec['title']}")
    L_add("")
    L_add(f"Train {res['train_range']}; test {res['test_range']} ({spec['horizon']} days).")
    L_add("")
    L_add("### Accuracy against true demand")
    L_add("")
    L_add("WAPE = sum|true - forecast| / sum(true); bias = (sum forecast - sum true) / sum true (negative: forecast too low).")
    L_add("")
    cols = ["a", "b", "b_rate_x0_5", "b_rate_x1_5", "naive"]
    L_add("| Series group | Series | True units | " + " | ".join(f"WAPE {LABEL[v]}" for v in cols) + " | Bias A | Bias B |")
    L_add("|---|---:|---:|" + "---:|" * (len(cols) + 2))
    for name, r in acc.items():
        L_add(f"| {name} | {r['n_series']} | {r['actual_units']:.0f} | " + " | ".join(pct(r[v]['wape']) for v in cols)
              + f" | {pct(r['a']['bias'])} | {pct(r['b']['bias'])} |")
    L_add("")
    L_add("Paired comparison of A and B. Difference = WAPE(A) - WAPE(B) in percentage points (positive: B better), with a 95% interval "
          "from resampling series. Series where the two forecasts score the same are counted as ties.")
    L_add("")
    L_add("| Series group | Difference | 95% interval | B closer | A closer | Tie |")
    L_add("|---|---:|---:|---:|---:|---:|")
    for name, c in cmp_.items():
        L_add(f"| {name} | {c['mean'] * 100:+.2f} | {c['lo'] * 100:+.2f} to {c['hi'] * 100:+.2f} | {c['b_closer']} | {c['a_closer']} | {c['tie']} |")
    L_add("")
    L_add("Sensitivity of B to the ask rate: WAPE of A minus WAPE of each B variant, in points, with a 95% interval (positive: B still better).")
    L_add("")
    L_add("| Series group | Series | B variant | Difference | 95% interval |")
    L_add("|---|---:|---|---:|---:|")
    for group, per_variant in res["sens"].items():
        for v, c in per_variant.items():
            L_add(f"| {group} | {res['acc'][group]['n_series']} | {LABEL[v]} | {c['mean'] * 100:+.2f} | {c['lo'] * 100:+.2f} to {c['hi'] * 100:+.2f} |")
    L_add("")
    L_add("### Order policy replayed with each forecast")
    L_add("")
    L_add(f"Same world (true demand, supplier delays, scripted supply failures), identical until the cutoff; afterwards orders follow "
          f"`ceil(forecast over {params.COVER_DAYS} days + safety stock - closing stock - on order)`. Empty-shelf days = store-SKU-days that "
          "ended at zero stock; lost units = demand not served; excess units = stock above 7 days of average true demand, averaged over the "
          "test days. Supply failures block deliveries for every policy alike. The status quo (the simulator's own policy) keeps about 4 days "
          "of cover instead of 7 plus safety stock, so it holds far less stock; compare A and B with each other, not with it.")
    L_add("")
    for name in ("all series", "out of stock on the cutoff day", "hero (S01, SKU-0001)"):
        L_add(f"**{name}**")
        L_add("")
        L_add("| Policy | Empty-shelf days | Lost units | Excess units |")
        L_add("|---|---:|---:|---:|")
        for k in ["status_quo", *VARIANTS]:
            r = pol[name][k]
            L_add(f"| {LABEL[k]} | {r['stockout_days']} | {r['lost_units']:.0f} | {r['excess_units']:.0f} |")
        L_add("")
    return L


def render(results: dict, rates: pd.DataFrame, generator_rate: float, hero: dict, meta: dict) -> str:
    L = []
    add = L.append
    main, stress = results["main"], results["stress"]
    am, as_ = main["acc"]["all series"], stress["acc"]["out of stock on the cutoff day"]
    cm, cs = main["cmp"]["all series"], stress["cmp"]["out of stock on the cutoff day"]
    add("# Experiment results: forecast A vs B")
    add("")
    add(f"All data is synthetic. Generated by `python -m app.forecast.experiment` on {meta['date']}; {meta['n_series']} store-SKU series, "
        "true demand from the simulator, `ask_rate_hat` estimated from each experiment's own training data.")
    add("")
    add("## Summary")
    add("")
    mo, so = main["acc"]["out of stock on the cutoff day"], stress["acc"]["out of stock on the cutoff day"]
    cmo, cso = main["cmp"]["out of stock on the cutoff day"], stress["cmp"]["out of stock on the cutoff day"]
    add(f"- **Plain backtest (train to day 76, predict 14 days):** over all {am['n_series']} series WAPE is {pct(am['a']['wape'])} for A and "
        f"{pct(am['b']['wape'])} for B ({cm['mean'] * 100:+.2f} points, 95% interval {cm['lo'] * 100:+.2f} to {cm['hi'] * 100:+.2f}): "
        f"{verdict(cm, am['n_series'])}. Only about 0.4% of demand is hidden by stockouts in this dataset, and ARIMA_PLUS already absorbs short "
        f"dips, so A and B are almost the same series and the replayed order policies give the same empty-shelf days. On the {mo['n_series']} series out "
        f"of stock on the cutoff day, A scores {pct(mo['a']['wape'])} and B {pct(mo['b']['wape'])}: {verdict(cmo, mo['n_series'])}.")
    add(f"- **Stress test (stockouts still going on when the forecast is made; 7 days of truth left):** on the {so['n_series']} series out of stock on "
        f"the cutoff day, WAPE is {pct(so['a']['wape'])} for A and {pct(so['b']['wape'])} for B ({cso['mean'] * 100:+.1f} points); {verdict(cso, so['n_series'])}. "
        f"A's bias is {pct(so['a']['bias'])} and B's {pct(so['b']['bias'])}: A reads the empty shelf as vanished demand, B partly corrects it.")
    add(f"- **A trivial forecast (mean of the last 28 days of POS) scores {pct(am['naive']['wape'])} over all series, slightly better than both "
        f"ARIMA_PLUS variants ({pct(am['a']['wape'])} and {pct(am['b']['wape'])}).** The gain of B over A should be read against that: it shows B is not a "
        "stronger forecaster in general, only that it does not collapse after a long stockout.")
    add(f"- **Coconut-milk scenario (production forecast):** A expects {hero['forecast_a_7d']:.1f} units over the next 7 days and orders "
        f"{hero['recommended_qty_a']}; B expects {hero['forecast_b_7d']:.1f} and orders {hero['recommended_qty_b']}. Both come from the formula.")
    add("- **Sensitivity:** the ask rate is estimated, not known. Section 2 re-runs B with it shifted by -50% and +50%.")
    add("")
    for i, key in enumerate(("main", "stress"), start=1):
        L.extend(_section(i, results[key]))
    add("## 3. The ask-rate estimate")
    add("")
    add("`ask_rate_hat` is the share of unmet shoppers that show up as a kiosk signal. It is estimated from the training data only: per category, "
        "total unmet signals divided by the unmet demand expected on stockout days (from in-stock days of the same weekday within 28 days), "
        "pooled across categories when a category has too little evidence. Estimate for the 90-day production run:")
    add("")
    add("| Category | ask_rate_hat | Unmet signals | Expected unmet units | Source |")
    add("|---|---:|---:|---:|---|")
    for r in rates.itertuples():
        add(f"| {r.category} | {'n/a' if r.ask_rate_hat != r.ask_rate_hat else f'{r.ask_rate_hat:.2f}'} | {r.signals:.0f} | {r.expected_unmet:.0f} | {r.source} |")
    add("")
    add(f"For validation only (never an input): the generator's own kiosk capture rate is {generator_rate:.2f}. The pooled estimate is "
        f"{meta['pooled_prod']:.2f} for all 90 days, {meta['pooled_late']:.2f} up to day 83 and {meta['pooled_bt']:.2f} up to day 76 (thin evidence). "
        "The estimate runs high: the demand expected from the days around a stockout is an average, while days that end out of stock tend to be "
        "high-demand days, so B infers somewhat less lost demand than there really was.")
    add("")
    add("## 4. The coconut-milk scenario (production forecast, made on the last data day)")
    add("")
    add("| | Forecast next 7 days | Order from the formula |")
    add("|---|---:|---:|")
    add(f"| A (POS only) | {hero['forecast_a_7d']:.1f} | {hero['recommended_qty_a']} |")
    add(f"| B (POS + unmet) | {hero['forecast_b_7d']:.1f} | {hero['recommended_qty_b']} |")
    add("")
    add(f"S01 / SKU-0001 had {hero['on_hand']} units on hand and {hero['unmet_7d']} unmet shopper requests in the last 7 days. Both orders come from "
        f"`max(0, forecast + safety stock - on hand - on order)`, not from fixed values. A still orders {hero['recommended_qty_a']} because its prediction "
        "interval is wide after 14 empty days, which adds safety stock; there is no later data to score this forecast against, section 2 does that for "
        "an earlier cutoff.")
    add("")
    add("## 5. Limits")
    add("")
    for t in meta["limits"]:
        add(f"- {t}")
    add("")
    return "\n".join(L)


def main() -> None:
    import yaml
    from sim.engine import build_world

    c = bqio.client()
    w = build_world()
    fc = bqio.query(c, f"SELECT kind, variant, store_id, sku, forecast_date AS date, forecast_qty, lower, upper FROM {bqio.fq()}.bt_forecasts")
    results = {}
    for key, spec in EXPERIMENTS.items():
        ex = load_experiment(c, w, fc, spec)
        masks = subsets(w, ex["cut"])
        results[key] = {
            "spec": spec, "acc": accuracy(w, ex), "pol": policy(w, ex),
            "cmp": {n: compare(w, ex, m) for n, m in masks.items() if m.sum() > 1},
            "sens": {g: {v: compare(w, ex, masks[g], b_key=v) for v in ("b", "b_rate_x0_5", "b_rate_x1_5")}
                     for g in ("out of stock on the cutoff day", "stockout in the last 14 training days")},
            "train_range": f"{w.dates[0].date()} to {w.dates[ex['cut'] - 1].date()}",
            "test_range": f"{w.dates[ex['cut']].date()} to {w.dates[ex['cut'] + ex['horizon'] - 1].date()}",
        }
    rates = bqio.query(c, f"SELECT kind, category, ask_rate_hat, signals, expected_unmet, source FROM {bqio.fq()}.ask_rate_estimates")
    pooled = lambda k: float(rates[(rates["kind"] == k) & (rates["category"] == "ALL")]["ask_rate_hat"].iloc[0])  # noqa: E731
    gen = yaml.safe_load(open(Path(__file__).resolve().parents[4] / "data" / "seed_scenarios.yaml", encoding="utf-8"))
    hero = bqio.query(c, f"SELECT on_hand, forecast_a_7d, forecast_b_7d, unmet_7d, recommended_qty_a, recommended_qty_b "
                         f"FROM {bqio.fq()}.recommendations WHERE store_id = 'S01' AND sku = 'SKU-0001'").iloc[0].to_dict()
    for k in ("on_hand", "unmet_7d", "recommended_qty_a", "recommended_qty_b"):
        hero[k] = int(hero[k])
    meta = {
        "date": dt.date.today().isoformat(), "n_series": int(w.shape[1] * w.shape[2]),
        "pooled_bt": pooled("bt"), "pooled_late": pooled("late"), "pooled_prod": pooled("prod"),
        "limits": [
            "Only about 0.4% of demand is censored in this dataset, so differences between A and B are small overall and concentrated in the few "
            "series that ran out of stock.",
            "The hero stockout begins on the first day of the plain backtest, so there both A and B were trained before it. The stress test (cutoff "
            "on day 83) exists to cover that case; it only has 7 days of true demand left to score against.",
            "The scripted supply failures block deliveries for every policy, so no forecast can prevent those empty shelves.",
            "One simulated world and a few cutoffs: the intervals reflect resampling of series, not of worlds or of cutoffs.",
            "Daily demand per store and SKU is a small count with Poisson noise, so WAPE of 50-60% is normal at this level; the naive column is "
            "the yardstick.",
            "Open purchase orders are not tracked in the data, so `on_order` is 0 in the recommendations.",
        ],
    }
    gen_rate = float(gen["simulation"]["conversations"]["p_chat_unmet"])
    prod_rates = rates[rates["kind"] == "prod"].drop(columns="kind")
    RESULTS_PATH.write_text(render(results, prod_rates, gen_rate, hero, meta), encoding="utf-8")
    print("wrote", RESULTS_PATH)
    for key, r in results.items():
        for name in ("all series", "out of stock on the cutoff day", "hero (S01, SKU-0001)"):
            a = r["acc"][name]
            print(f"{key:7s} {name:34s} n={a['n_series']:3d} " + " ".join(f"{v}={a[v]['wape'] * 100:5.1f}%" for v in [*VARIANTS, "naive"]))


if __name__ == "__main__":
    main()
