"""Load simulation config and reference tables."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = DATA_DIR / "out"


@dataclass(frozen=True)
class SimConfig:
    raw: dict
    scenarios: list[dict]

    @property
    def sim(self) -> dict:
        return self.raw["simulation"]

    @property
    def end_date(self) -> dt.date:
        v = self.sim["end_date"]
        return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))

    @property
    def days(self) -> int:
        return int(self.sim["days"])

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.date_range(end=pd.Timestamp(self.end_date), periods=self.days, freq="D")

    @property
    def stores(self) -> list[dict]:
        return self.sim["stores"]

    @property
    def capture_rate(self) -> float:
        return float(self.sim["assumed_capture_rate"])


def load_config(path: Path | None = None) -> SimConfig:
    path = path or DATA_DIR / "seed_scenarios.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SimConfig(raw=raw, scenarios=raw.get("scenarios", []))


def load_master() -> pd.DataFrame:
    """Full product_master (both carried and NC rows). is_carried as bool, brand/synonyms never NaN."""
    df = pd.read_csv(DATA_DIR / "product_master.csv").fillna({"brand": "", "synonyms": "", "aisle": ""})
    df["is_carried"] = df["is_carried"].astype(str).str.strip().str.lower().isin(("true", "1"))
    return df


def load_sku_params() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sim" / "sku_params.csv")
