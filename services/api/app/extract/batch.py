"""Batch signal extraction over the historical conversations table (build plan §6.6).

    # from services/api, with PYTHONPATH=.:../../data
    python -m app.extract.batch                                   # offline template extractor
    python -m app.extract.batch --llm gemini --project <ID> --location global

Reads data/out/conversations.csv + data/product_master.csv, writes data/out/demand_signals.csv
(contract columns, model_version = extractor-v1-YYYYMMDD). Load it to BigQuery with sim/load_bq.py.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .catalog import load_catalog
from .core import DEMAND_SIGNALS_COLUMNS, extract_one

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = REPO_ROOT / "data" / "out"
DEFAULT_MASTER = REPO_ROOT / "data" / "product_master.csv"


def _read_conversations(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _run_gemini(convs, catalog, project, location, model, cache_path: Path) -> dict:
    from .client import extract_item, make_client

    cache: dict[str, dict] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                cache[o["id"]] = o["data"]
    todo = [c for c in convs if c["conversation_id"] not in cache]
    print(f"Gemini extract: {len(convs) - len(todo)} cached, {len(todo)} to call ({model})")
    client = make_client(project, location)
    workers = int(os.getenv("GEMINI_WORKERS", "8"))
    with ThreadPoolExecutor(workers) as ex, cache_path.open("a", encoding="utf-8") as fh:
        for conv, item in zip(todo, ex.map(
                lambda c: extract_item(client, model, c.get("transcript"), catalog), todo)):
            cache[conv["conversation_id"]] = item
            fh.write(json.dumps({"id": conv["conversation_id"], "data": item}, ensure_ascii=False) + "\n")
    return cache


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--llm", choices=["template", "gemini"], default="template")
    ap.add_argument("--src", default=str(DEFAULT_OUT), help="dir with conversations.csv (output dir too)")
    ap.add_argument("--master", default=str(DEFAULT_MASTER))
    ap.add_argument("--project", default=os.getenv("GCP_PROJECT"))
    ap.add_argument("--location", default=os.getenv("GCP_LOCATION", "global"))
    ap.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    ap.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"), help="model_version suffix")
    args = ap.parse_args()

    src = Path(args.src)
    convs = _read_conversations(src / "conversations.csv")
    catalog = load_catalog(args.master)
    model_version = f"extractor-v1-{args.date}"
    print(f"Extracting {len(convs)} conversations via {args.llm} -> model_version={model_version}")

    llm_out = (_run_gemini(convs, catalog, args.project, args.location, args.model,
                           src / "_extract_cache.jsonl") if args.llm == "gemini" else {})

    rows = [extract_one(c, catalog, llm_out.get(c["conversation_id"]) if args.llm == "gemini" else None,
                        model_version) for c in convs]

    out_path = src / "demand_signals.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DEMAND_SIGNALS_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    outcomes = Counter(r["outcome"] for r in rows)
    sku_null = sum(1 for r in rows if r["sku"] is None)
    print(f"  {out_path.name}: {len(rows)} rows | outcomes {dict(outcomes)} | sku NULL {sku_null}")
    print("Next: python -m app.extract.eval")


if __name__ == "__main__":
    main()
