"""Small BigQuery helpers for the forecast pipeline (no pyarrow needed: rows in, rows out)."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ..config import settings


def client():
    from google.cloud import bigquery

    return bigquery.Client(project=settings.gcp_project, location=settings.gcp_location)


def fq() -> str:
    return f"`{settings.gcp_project}.{settings.bq_dataset}`"


def query(c, sql: str, params: dict | None = None) -> pd.DataFrame:
    from google.cloud import bigquery

    qp = [bigquery.ScalarQueryParameter(k, "DATE" if isinstance(v, dt.date) else "STRING" if isinstance(v, str) else
                                        "FLOAT64" if isinstance(v, float) else "INT64", v)
          for k, v in (params or {}).items()]
    rows = c.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=qp)).result()
    return pd.DataFrame([dict(r) for r in rows])


def execute(c, sql: str) -> None:
    c.query(sql).result()


def load_rows(c, table: str, df: pd.DataFrame, schema: list | None = None, truncate: bool = True) -> None:
    """Replace (or append to) `table` with the frame's rows; dates/timestamps become ISO strings."""
    from google.cloud import bigquery

    records = []
    for rec in df.to_dict("records"):
        records.append({k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime, pd.Timestamp)) else
                            None if (v is None or (isinstance(v, float) and v != v)) else v) for k, v in rec.items()})
    cfg = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE" if truncate else "WRITE_APPEND",
        schema=schema, autodetect=schema is None, source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    c.load_table_from_json(records, f"{settings.gcp_project}.{settings.bq_dataset}.{table}", job_config=cfg).result()


def load_facts(c, cutoff: dt.date) -> pd.DataFrame:
    """One row per store, SKU and day up to `cutoff`: POS units, stockout flag, kiosk unmet signals."""
    F = fq()
    df = query(c, f"""
        SELECT p.date, p.store_id, p.sku, m.category, p.qty_sold, e.is_stockout, COALESCE(u.unmet_signals, 0) AS unmet_signals
        FROM {F}.pos_sales p
        JOIN {F}.stock_events e USING (date, store_id, sku)
        JOIN {F}.product_master m USING (sku)
        LEFT JOIN (SELECT date, store_id, sku, SUM(qty) AS unmet_signals FROM {F}.v_signals
                   WHERE sku IS NOT NULL AND outcome IN ('out_of_stock', 'substituted') GROUP BY 1, 2, 3) u
          USING (date, store_id, sku)
        WHERE p.date <= @cutoff ORDER BY store_id, sku, date""", {"cutoff": cutoff})
    df["date"] = pd.to_datetime(df["date"])
    df["is_stockout"] = df["is_stockout"].astype(bool)
    df["qty_sold"] = df["qty_sold"].astype(float)
    df["unmet_signals"] = df["unmet_signals"].astype(float)
    return df.reset_index(drop=True)


def data_span(c) -> tuple[dt.date, dt.date]:
    r = query(c, f"SELECT MIN(date) AS d0, MAX(date) AS d1 FROM {fq()}.pos_sales").iloc[0]
    return r["d0"], r["d1"]
