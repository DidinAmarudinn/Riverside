"""Generate the synthetic world and write CSVs to data/out/.

    PYTHONPATH=data python -m sim.run            # from the repo root
"""
from __future__ import annotations

import argparse
import json

from .config import OUT_DIR, load_config
from .conversations import generate_conversations
from .engine import build_world, to_frames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=None, help="override simulation.seed")
    args = ap.parse_args()

    cfg = load_config()
    if args.seed is not None:
        cfg.sim["seed"] = args.seed
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    world = build_world(cfg)
    for name, df in to_frames(world).items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"{name:14s} {len(df):>8,} rows")

    conv = generate_conversations(world)
    conv.to_csv(OUT_DIR / "conversations.csv", index=False)
    print(f"{'conversations':14s} {len(conv):>8,} rows")

    (OUT_DIR / "scenarios_resolved.json").write_text(json.dumps(world.resolved_scenarios, indent=2, default=str))

    unmet = (world.demand - world.sales).sum()
    print(f"\ntrue demand {world.demand.sum():,} units | POS {world.sales.sum():,} | "
          f"censored {unmet:,} ({unmet / world.demand.sum():.1%}) | "
          f"stockout SKU-store-days {(world.closing == 0).sum():,}")


if __name__ == "__main__":
    main()
