"""BigQuery repository (DATA_BACKEND=gcp): catalog, stores and stock come from the shared `demand_radar` dataset.

Reads are loaded once at startup (a few hundred rows). Live stock = closing stock of the latest day in
`stock_events`; demo overrides (restock, empty shelf) live in memory on top of it.
"""
from __future__ import annotations

import math
import threading

ROAD_FACTOR = 1.0  # distances are straight-line (haversine); kept explicit so a road factor can be added


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _pack_label(value, unit) -> str:
    if value is None:
        return ""
    return f"{value:g} {unit or ''}".strip()


class GcpRepo:
    def __init__(self, project: str, dataset: str, client=None, max_bytes_billed: int = 100_000_000):
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=project)
        self._bq = client
        self._fq = f"`{project}.{dataset}`"
        self._max_bytes = max_bytes_billed
        self._lock = threading.Lock()
        self._load()

    # -- load -------------------------------------------------------------------------------
    def _rows(self, sql: str) -> list[dict]:
        from google.cloud import bigquery

        cfg = bigquery.QueryJobConfig(maximum_bytes_billed=self._max_bytes)
        return [dict(r) for r in self._bq.query(sql, job_config=cfg).result()]

    def _load(self) -> None:
        fq = self._fq
        self._products = []
        for r in self._rows(
            f"SELECT sku, name, brand, category, aisle, pack_size, unit, price_idr, shelf_life_days, synonyms "
            f"FROM {fq}.product_master WHERE is_carried ORDER BY sku"
        ):
            self._products.append({
                "sku": r["sku"], "name": r["name"], "brand": r["brand"] or "", "category": r["category"] or "",
                "pack_size": _pack_label(r["pack_size"], r["unit"]), "price_idr": int(r["price_idr"]),
                "shelf_location": r["aisle"] or "", "shelf_life_days": r["shelf_life_days"],
                "synonyms": list(r["synonyms"] or []),
            })
        self._by_sku = {p["sku"]: p for p in self._products}
        self._stores = [
            {"id": r["store_id"], "name": r["name"], "city": r["city"], "lat": r["lat"], "lng": r["lng"]}
            for r in self._rows(f"SELECT store_id, name, city, lat, lng FROM {fq}.stores ORDER BY store_id")
        ]
        self._baseline = {
            (r["store_id"], r["sku"]): int(r["closing_stock"])
            for r in self._rows(
                f"SELECT store_id, sku, closing_stock FROM {fq}.stock_events "
                f"WHERE date = (SELECT MAX(date) FROM {fq}.stock_events)"
            )
        }
        with self._lock:
            self._live = dict(self._baseline)

    def refresh(self) -> None:
        """Re-read catalog, stores and stock from BigQuery (drops demo overrides)."""
        self._load()

    # -- Repository -------------------------------------------------------------------------
    def products(self) -> list[dict]:
        return list(self._products)

    def get_product(self, sku: str) -> dict | None:
        return self._by_sku.get(sku)

    def stores(self) -> list[dict]:
        return [{"id": s["id"], "name": s["name"]} for s in self._stores]

    def get_store(self, store_id: str) -> dict | None:
        s = next((s for s in self._stores if s["id"] == store_id), None)
        return {"id": s["id"], "name": s["name"]} if s else None

    def distance_km(self, a: str, b: str) -> float | None:
        if a == b:
            return 0.0
        sa = next((s for s in self._stores if s["id"] == a), None)
        sb = next((s for s in self._stores if s["id"] == b), None)
        if not sa or not sb or None in (sa["lat"], sa["lng"], sb["lat"], sb["lng"]):
            return None
        return round(_haversine_km(sa["lat"], sa["lng"], sb["lat"], sb["lng"]) * ROAD_FACTOR, 1)

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
            self._live = dict(self._baseline)
