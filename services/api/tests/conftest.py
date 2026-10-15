"""Shared fixtures: a tiny in-memory world (3 stores, 8 SKUs) so tests do not need `make sim`."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from app.data import set_repo
from app.data.local import LocalRepo
from app.signals import get_publisher, reset_publisher_cache

PRODUCT_COLS = ["sku", "name", "brand", "category", "subcategory", "pack_size", "price_idr",
                "shelf_life_days", "perishable", "shelf_location"]
PRODUCTS = [
    ("SKU-0001", "Santan Kotak Kara 65 ml", "Kara", "Cooking Essentials", "Coconut Milk", "65 ml", 4500, "A1-2"),
    ("SKU-0002", "Santan Kotak Kara 200 ml", "Kara", "Cooking Essentials", "Coconut Milk", "200 ml", 11500, "A1-3"),
    ("SKU-0003", "Santan Kotak Sasa 65 ml", "Sasa", "Cooking Essentials", "Coconut Milk", "65 ml", 4200, "A1-1"),
    ("SKU-0004", "Santan Kotak Sasa 200 ml", "Sasa", "Cooking Essentials", "Coconut Milk", "200 ml", 10500, "A1-4"),
    ("SKU-0005", "Minyak Goreng Bimoli 2 L", "Bimoli", "Cooking Essentials", "Cooking Oil", "2 L", 37000, "A2-1"),
    ("SKU-0006", "Minyak Goreng Filma 2 L", "Filma", "Cooking Essentials", "Cooking Oil", "2 L", 36000, "A2-2"),
    ("SKU-0007", "Telur Ayam Peternak Lokal 10 pcs", "Peternak Lokal", "Dairy & Eggs", "Eggs", "10 pcs", 28000, "C1-1"),
    ("SKU-0008", "Mi Goreng Indomie 85 g", "Indomie", "Instant Food", "Instant Noodles", "85 g", 3200, "B1-1"),
]
# closing stock on the last simulated day, per store: S01, S02, S03
STOCK = {
    "SKU-0001": (0, 40, 12), "SKU-0002": (8, 5, 0), "SKU-0003": (20, 0, 7), "SKU-0004": (0, 0, 0),
    "SKU-0005": (30, 0, 9), "SKU-0006": (4, 11, 0), "SKU-0007": (15, 15, 15), "SKU-0008": (100, 80, 90),
}
CONFIG = {
    "simulation": {
        "stores": [
            {"id": "S01", "name": "Radar Mart Cipete", "size_factor": 1.0},
            {"id": "S02", "name": "Radar Mart BSD", "size_factor": 0.8},
            {"id": "S03", "name": "Radar Mart Kelapa Gading", "size_factor": 0.9},
        ],
        "store_distances_km": {"S01": {"S02": 21, "S03": 24}, "S02": {"S03": 39}},
    },
    "scenarios": [
        {"id": "hero", "store_id": "S01", "product": "Santan Kotak Kara 65 ml",
         "demo": {"live_stock": 0, "restock_units": 60}},
    ],
}


def write_world(root: Path, stock=STOCK) -> Path:
    (root / "out").mkdir(parents=True, exist_ok=True)
    with open(root / "product_master.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(PRODUCT_COLS)
        for sku, name, brand, cat, sub, size, price, shelf in PRODUCTS:
            w.writerow([sku, name, brand, cat, sub, size, price, 365, 0, shelf])
    with open(root / "out" / "stock_events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "store_id", "sku", "opening_stock", "received_units", "closing_stock", "stockout_flag"])
        for sku, per_store in stock.items():
            for sid, units in zip(("S01", "S02", "S03"), per_store):
                w.writerow(["2026-10-11", sid, sku, 999, 0, 999, 0])  # older row must be ignored
                w.writerow(["2026-10-12", sid, sku, units, 0, units, int(units == 0)])
    (root / "seed_scenarios.yaml").write_text(yaml.safe_dump(CONFIG), encoding="utf-8")
    return root


@pytest.fixture
def world(tmp_path) -> LocalRepo:
    repo = LocalRepo(write_world(tmp_path))
    set_repo(repo)
    yield repo
    set_repo(None)


@pytest.fixture
def publisher():
    """Fresh in-memory publisher (the default when DATA_BACKEND=local)."""
    reset_publisher_cache()
    yield get_publisher()
    reset_publisher_cache()
