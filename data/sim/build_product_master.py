"""Build data/product_master.csv (contract §4.1) + the sim-only data/sim/sku_params.csv.

product_master.csv holds exactly the contract columns and BOTH carried SKUs and the ~20
`is_carried = false` assortment-gap rows (SKU `NC-xxx`). Fields only the simulator needs
(subcategory, perishable, popularity, base demand) live in sku_params.csv, keyed by sku.

Run from the repo root:  PYTHONPATH=data python -m sim.build_product_master
"""
from __future__ import annotations

import csv
from pathlib import Path

from .catalog import FAMILIES, NOT_STOCKED, nc_sku

DATA_DIR = Path(__file__).resolve().parents[1]

# Mean units/day/store for a family at each popularity tier (split across sizes by share).
POP_BASE = {1: 0.6, 2: 1.6, 3: 3.4, 4: 6.5, 5: 11.0}

# Contract columns (docs/api-contract.md §1 / sql/01_tables.sql). synonyms is pipe-joined;
# the BigQuery loader splits it into ARRAY<STRING>.
MASTER_COLUMNS = [
    "sku", "name", "brand", "category", "pack_size", "unit",
    "price_idr", "shelf_life_days", "aisle", "synonyms", "is_carried",
]
PARAM_COLUMNS = ["sku", "subcategory", "perishable", "popularity", "base_units"]


def unit_from_pack_size(label: str) -> str:
    """Grocery unit of measure parsed from a pack-size label ('65 ml' -> 'ml', '10 pcs' -> 'pcs')."""
    tokens = label.lower().replace("x", " ").split()
    known = {"ml", "l", "g", "kg", "gr", "gram", "liter"}
    for tok in tokens:
        if tok in known:
            return {"gr": "g", "gram": "g", "liter": "L", "l": "L"}.get(tok, tok)
    # count-based packs: pcs / pack / sachet / ikat / sisir / ekor / papan / slices / bags ...
    for tok in reversed(tokens):
        if not any(ch.isdigit() for ch in tok):
            return tok
    return "pcs"


def build_rows() -> tuple[list[dict], list[dict]]:
    master, params = [], []
    n = 0
    for fam in FAMILIES:
        for label, price, share in fam.sizes:
            n += 1
            sku = f"SKU-{n:04d}"
            master.append({
                "sku": sku,
                "name": " ".join(p for p in (fam.product, fam.brand, label) if p),
                "brand": fam.brand,
                "category": fam.category,
                "pack_size": label,
                "unit": unit_from_pack_size(label),
                "price_idr": price,
                "shelf_life_days": fam.shelf_life_days,
                "aisle": f"{fam.aisle}-{(n % 4) + 1}",
                "synonyms": "|".join(fam.aliases),
                "is_carried": "true",
            })
            params.append({
                "sku": sku,
                "subcategory": fam.subcategory,
                "perishable": int(fam.shelf_life_days <= 30),
                "popularity": fam.pop,
                "base_units": round(POP_BASE[fam.pop] * share, 3),
            })

    # Assortment gaps: asked for but never stocked (is_carried = false, no sim params).
    for i, item in enumerate(NOT_STOCKED):
        master.append({
            "sku": nc_sku(i),
            "name": item.name,
            "brand": "",
            "category": item.category,
            "pack_size": item.pack_size,
            "unit": unit_from_pack_size(item.pack_size),
            "price_idr": item.price,
            "shelf_life_days": "",
            "aisle": "",
            "synonyms": "|".join(item.aliases),
            "is_carried": "false",
        })
    return master, params


def main() -> None:
    master, params = build_rows()
    carried = sum(1 for r in master if r["is_carried"] == "true")
    assert 150 <= carried <= 300, f"unexpected carried SKU count: {carried}"

    with open(DATA_DIR / "product_master.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_COLUMNS)
        w.writeheader()
        w.writerows(master)

    with open(DATA_DIR / "sim" / "sku_params.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PARAM_COLUMNS)
        w.writeheader()
        w.writerows(params)

    print(f"product_master.csv: {len(master)} rows ({carried} carried, {len(NOT_STOCKED)} not-carried); "
          f"sku_params.csv: {len(params)} rows")


if __name__ == "__main__":
    main()
