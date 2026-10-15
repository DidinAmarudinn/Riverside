"""Load the simulated CSVs into BigQuery and build the contract tables + views (build plan §5.9).

    # from the repo root, after `python -m sim.run` (and optionally the extractor)
    PYTHONPATH=data python -m sim.load_bq --project <ID> --location us-central1
    PYTHONPATH=data python -m sim.load_bq --project <ID> --skip-load   # re-run SQL only

Runs sql/01_tables.sql (DDL), loads every table from data/out/ (+ data/product_master.csv), then
sql/02_views.sql (views) and sql/05_bootstrap_signals.sql (seed demand_signals from ground truth).
Placeholders ${PROJECT} / ${DATASET} are rendered here, so the .sql files never hardcode a project.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, OUT_DIR

REPO_ROOT = DATA_DIR.parent
SQL_DIR = REPO_ROOT / "sql"

# table -> source CSV (relative to its dir). demand_signals is optional (only if the extractor ran).
SOURCES = {
    "stores": OUT_DIR / "stores.csv",
    "product_master": DATA_DIR / "product_master.csv",
    "calendar_context": OUT_DIR / "calendar_context.csv",
    "true_demand": OUT_DIR / "true_demand.csv",
    "stock_events": OUT_DIR / "stock_events.csv",
    "pos_sales": OUT_DIR / "pos_sales.csv",
    "conversations": OUT_DIR / "conversations.csv",
    "demand_signals": OUT_DIR / "demand_signals.csv",
}
BOOL_COLS = {"is_carried", "is_stockout", "is_payday_window", "is_holiday", "is_ramadan", "is_lebaran_window"}
DATE_COLS = {"date"}
TS_COLS = {"ts"}


def _coerce(table: str, df: pd.DataFrame) -> pd.DataFrame:
    if table == "product_master":
        df["synonyms"] = df["synonyms"].fillna("").apply(lambda s: [x for x in str(s).split("|") if x])
    for col in df.columns:
        if col in BOOL_COLS:
            df[col] = df[col].astype(str).str.strip().str.lower().isin(("true", "1"))
        elif col in DATE_COLS:
            df[col] = pd.to_datetime(df[col]).dt.date
        elif col in TS_COLS:
            df[col] = pd.to_datetime(df[col], utc=False)
    return df


def _render(sql: str, project: str, dataset: str) -> str:
    return sql.replace("${PROJECT}", project).replace("${DATASET}", dataset)


def _strip_comments(sql: str) -> str:
    """Drop `-- ...` comments (full-line and trailing) so they don't swallow adjacent statements."""
    out = []
    for line in sql.splitlines():
        idx = line.find("--")
        out.append(line if idx == -1 else line[:idx])
    return "\n".join(out)


def _run_sql_file(client, path: Path, project: str, dataset: str) -> None:
    text = _strip_comments(_render(path.read_text(encoding="utf-8"), project, dataset))
    statements = [s.strip() for s in text.split(";") if s.strip()]
    print(f"  {path.name}: {len(statements)} statement(s)")
    for stmt in statements:
        client.query(stmt).result()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True)
    ap.add_argument("--dataset", default="demand_radar")
    ap.add_argument("--location", default="us-central1")
    ap.add_argument("--skip-load", action="store_true", help="run SQL only, do not reload tables")
    args = ap.parse_args()

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project, location=args.location)
    print(f"Project {args.project} · dataset {args.dataset} · {args.location}")

    print("DDL (sql/01_tables.sql):")
    _run_sql_file(client, SQL_DIR / "01_tables.sql", args.project, args.dataset)

    if not args.skip_load:
        print("Loading tables:")
        for table, path in SOURCES.items():
            if not path.exists():
                print(f"  {table:16s} skipped (no {path.name})")
                continue
            df = _coerce(table, pd.read_csv(path))
            table_id = f"{args.project}.{args.dataset}.{table}"
            job_config = bigquery.LoadJobConfig(
                schema=client.get_table(table_id).schema,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )
            client.load_table_from_dataframe(df, table_id, job_config=job_config).result()
            print(f"  {table:16s} {len(df):>8,} rows")

    print("Views (sql/02_views.sql):")
    _run_sql_file(client, SQL_DIR / "02_views.sql", args.project, args.dataset)
    print("Bootstrap signals (sql/05_bootstrap_signals.sql):")
    _run_sql_file(client, SQL_DIR / "05_bootstrap_signals.sql", args.project, args.dataset)

    _check_dod(client, args.project, args.dataset)


def _check_dod(client, project: str, dataset: str) -> None:
    """Light Definition-of-Done probes: the agent views return data (build plan §5 'view bisa di-query')."""
    ns = f"`{project}.{dataset}`"
    probes = {
        "demand_signals rows": f"SELECT COUNT(*) c FROM {ns}.demand_signals",
        "v_signals rows": f"SELECT COUNT(*) c FROM {ns}.v_signals",
        "v_assortment_gaps rows": f"SELECT COUNT(*) c FROM {ns}.v_assortment_gaps",
        "v_unmet_daily rows": f"SELECT COUNT(*) c FROM {ns}.v_unmet_daily",
        "v_lost_revenue_today rows": f"SELECT COUNT(*) c FROM {ns}.v_lost_revenue_today",
    }
    print("Definition of Done (BigQuery):")
    ok = True
    for name, q in probes.items():
        c = list(client.query(q).result())[0]["c"]
        ok &= c > 0
        print(f"  {'PASS' if c > 0 else 'FAIL'}  {name:<26} {c:,}")
    if not ok:
        raise SystemExit(1)
    print("Tables and views are populated.")


if __name__ == "__main__":
    main()
