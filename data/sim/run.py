"""Generate the synthetic world and write contract-shaped CSVs to data/out/.

    PYTHONPATH=data python -m sim.run            # from the repo root

Writes true_demand, stock_events, pos_sales, conversations, calendar_context and stores, copies
product_master.csv alongside them, then runs the Langkah 3 Definition-of-Done checks (exit 1 on failure).
"""
from __future__ import annotations

import argparse
import json
import shutil

import pandas as pd

from .config import DATA_DIR, OUT_DIR, load_config
from .conversations import generate_conversations
from .engine import build_calendar, build_stores, build_world, to_frames

# Exact column set each contract table must have (docs/api-contract.md §1).
EXPECTED_COLUMNS = {
    "true_demand": {"date", "store_id", "sku", "demand_qty"},
    "stock_events": {"date", "store_id", "sku", "opening_stock", "received_qty", "closing_stock", "is_stockout"},
    "pos_sales": {"date", "store_id", "sku", "qty_sold", "revenue_idr"},
    "conversations": {"conversation_id", "store_id", "ts", "channel", "transcript", "gt_sku", "gt_outcome"},
    "calendar_context": {"date", "is_payday_window", "is_holiday", "holiday_name",
                         "is_ramadan", "is_lebaran_window", "weather"},
    "stores": {"store_id", "name", "city", "lat", "lng"},
}
OUTCOME_VOCAB = {"purchased", "out_of_stock", "not_carried", "substituted", ""}


def validate(world, frames: dict[str, pd.DataFrame], cfg) -> None:
    """Langkah 3 DoD: contract columns, outcome vocabulary, row counts, hero facts."""
    errors: list[str] = []

    for name, cols in EXPECTED_COLUMNS.items():
        got = set(frames[name].columns)
        if got != cols:
            errors.append(f"{name}: columns {sorted(got)} != {sorted(cols)}")

    bad = set(frames["conversations"]["gt_outcome"]) - OUTCOME_VOCAB
    if bad:
        errors.append(f"conversations.gt_outcome has non-contract values: {bad}")

    n_rows = len(world.store_ids) * len(world.skus) * cfg.days
    for name in ("true_demand", "stock_events", "pos_sales"):
        if len(frames[name]) != n_rows:
            errors.append(f"{name}: {len(frames[name])} rows != expected {n_rows}")

    conv = frames["conversations"]
    for rs in world.resolved_scenarios:
        n = int(rs.get("unmet_conversations", 0) or 0)
        if n <= 0:
            continue
        s, k = world.store_index(rs["store_id"]), world.sku_index(rs["sku"])
        last5 = world.sales[-5:, s, k]
        if int(last5.sum()) != 0:
            errors.append(f"hero {rs['sku']}@{rs['store_id']}: POS last 5 days != 0 ({last5.tolist()})")
        got = int(((conv["gt_sku"] == rs["sku"]) & (conv["store_id"] == rs["store_id"])
                   & (conv["gt_outcome"] == "out_of_stock")).sum())
        if got != n:
            errors.append(f"hero {rs['sku']}@{rs['store_id']}: {got} unmet conversations != pinned {n}")

    if errors:
        print("\nDefinition of Done (Langkah 3) FAILED:")
        for e in errors:
            print(f"  - {e}")
        raise SystemExit(1)
    print("Definition of Done (Langkah 3): all checks passed.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=None, help="override simulation.seed")
    args = ap.parse_args()

    cfg = load_config()
    if args.seed is not None:
        cfg.sim["seed"] = args.seed
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    world = build_world(cfg)
    frames = to_frames(world)
    frames["conversations"] = generate_conversations(world)
    frames["calendar_context"] = build_calendar(cfg)
    frames["stores"] = build_stores(cfg)

    for name, df in frames.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"{name:16s} {len(df):>8,} rows")

    shutil.copyfile(DATA_DIR / "product_master.csv", OUT_DIR / "product_master.csv")
    (OUT_DIR / "scenarios_resolved.json").write_text(json.dumps(world.resolved_scenarios, indent=2, default=str))

    unmet = int((world.demand - world.sales).sum())
    print(f"\ntrue demand {world.demand.sum():,} units | POS {world.sales.sum():,} | "
          f"censored {unmet:,} ({unmet / world.demand.sum():.1%}) | "
          f"stockout SKU-store-days {(world.closing == 0).sum():,}\n")

    validate(world, frames, cfg)


if __name__ == "__main__":
    main()
