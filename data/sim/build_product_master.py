"""Build data/product_master.csv (+ sim-only sku_params and not_stocked tables).

Run from the repo root:  PYTHONPATH=data python -m sim.build_product_master
"""
from __future__ import annotations

import csv
from pathlib import Path

from .catalog import FAMILIES, NOT_STOCKED

DATA_DIR = Path(__file__).resolve().parents[1]

# Mean units/day/store for a family at each popularity tier (split across sizes by share).
POP_BASE = {1: 0.6, 2: 1.6, 3: 3.4, 4: 6.5, 5: 11.0}

MASTER_COLUMNS = [
    "sku", "name", "brand", "category", "subcategory", "pack_size",
    "price_idr", "shelf_life_days", "perishable", "shelf_location",
]


def build_rows() -> tuple[list[dict], list[dict]]:
    master, params = [], []
    n = 0
    for fam in FAMILIES:
        for label, price, share in fam.sizes:
            n += 1
            sku = f"SKU-{n:04d}"
            name = " ".join(p for p in (fam.product, fam.brand, label) if p)
            master.append({
                "sku": sku,
                "name": name,
                "brand": fam.brand,
                "category": fam.category,
                "subcategory": fam.subcategory,
                "pack_size": label,
                "price_idr": price,
                "shelf_life_days": fam.shelf_life_days,
                "perishable": int(fam.shelf_life_days <= 30),
                "shelf_location": f"{fam.aisle}-{(n % 4) + 1}",
            })
            params.append({
                "sku": sku,
                "popularity": fam.pop,
                "base_units": round(POP_BASE[fam.pop] * share, 3),
            })
    return master, params


def main() -> None:
    master, params = build_rows()
    assert 150 <= len(master) <= 300, f"unexpected SKU count: {len(master)}"

    with open(DATA_DIR / "product_master.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_COLUMNS)
        w.writeheader()
        w.writerows(master)

    with open(DATA_DIR / "sim" / "sku_params.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "popularity", "base_units"])
        w.writeheader()
        w.writerows(params)

    with open(DATA_DIR / "not_stocked_items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "category", "request_weight"])
        for item in NOT_STOCKED:
            w.writerow([item.name, item.category, item.weight])

    print(f"product_master.csv: {len(master)} SKUs; not_stocked_items.csv: {len(NOT_STOCKED)} items")


if __name__ == "__main__":
    main()
