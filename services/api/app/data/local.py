"""Local repository: product master + simulator output in `data/`, live stock held in memory."""
from __future__ import annotations

import csv
import threading
from pathlib import Path

import yaml


class LocalRepo:
    def __init__(self, data_dir: Path, stock_csv: Path | None = None):
        self._dir = Path(data_dir)
        self._stock_csv = Path(stock_csv) if stock_csv else self._dir / "out" / "stock_events.csv"
        with open(self._dir / "product_master.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["price_idr"] = int(r["price_idr"])
            r["perishable"] = int(r["perishable"])
            r["shelf_life_days"] = int(r["shelf_life_days"])
        self._products = rows
        self._by_sku = {r["sku"]: r for r in rows}
        with open(self._dir / "seed_scenarios.yaml", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f)
        sim = self._cfg["simulation"]
        self._stores = [{"id": s["id"], "name": s["name"]} for s in sim["stores"]]
        self._dist: dict[tuple[str, str], float] = {}
        for a, row in (sim.get("store_distances_km") or {}).items():
            for b, km in row.items():
                self._dist[(a, b)] = self._dist[(b, a)] = float(km)
        self._baseline = self._load_baseline()
        self._lock = threading.Lock()
        self._live: dict[tuple[str, str], int] = {}
        self.reset_live_stock()

    # -- load -------------------------------------------------------------------------------
    def _load_baseline(self) -> dict[tuple[str, str], int]:
        """Closing stock on the last simulated day = what is on the shelf 'now'."""
        if not self._stock_csv.exists():
            raise FileNotFoundError(f"{self._stock_csv} not found; generate it with `make sim`")
        last: dict[tuple[str, str], tuple[str, int]] = {}
        with open(self._stock_csv, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                key = (r["store_id"], r["sku"])
                if key not in last or r["date"] >= last[key][0]:
                    last[key] = (r["date"], int(r["closing_stock"]))
        return {k: v[1] for k, v in last.items()}

    def _scenario_overrides(self) -> dict[tuple[str, str], int]:
        by_name = {p["name"]: p["sku"] for p in self._products}
        out = {}
        for sc in self._cfg.get("scenarios", []):
            demo = sc.get("demo") or {}
            if "live_stock" in demo and sc.get("product") in by_name:
                out[(sc["store_id"], by_name[sc["product"]])] = int(demo["live_stock"])
        return out

    # -- Repository -------------------------------------------------------------------------
    def products(self) -> list[dict]:
        return list(self._products)

    def get_product(self, sku: str) -> dict | None:
        return self._by_sku.get(sku)

    def stores(self) -> list[dict]:
        return list(self._stores)

    def get_store(self, store_id: str) -> dict | None:
        return next((s for s in self._stores if s["id"] == store_id), None)

    def distance_km(self, a: str, b: str) -> float | None:
        return 0.0 if a == b else self._dist.get((a, b))

    def get_stock(self, store_id: str, sku: str) -> int | None:
        with self._lock:
            return self._live.get((store_id, sku))

    def stock_by_store(self, sku: str) -> dict[str, int]:
        with self._lock:
            return {s["id"]: self._live[(s["id"], sku)] for s in self._stores if (s["id"], sku) in self._live}

    def set_stock(self, store_id: str, sku: str, units: int) -> None:
        if (store_id, sku) not in self._baseline:
            raise KeyError(f"unknown store/SKU pair: {store_id}/{sku}")
        with self._lock:
            self._live[(store_id, sku)] = max(0, int(units))

    def reset_live_stock(self) -> None:
        with self._lock:
            self._live = {**self._baseline, **self._scenario_overrides()}
