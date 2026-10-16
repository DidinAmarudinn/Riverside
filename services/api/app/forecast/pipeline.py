"""Forecast pipeline: training series -> BigQuery ML ARIMA_PLUS -> forecasts -> recommendations.

    python -m app.forecast.pipeline series      # build fc_series_bt / fc_series_prod (+ ask_rate_estimates)
    python -m app.forecast.pipeline train       # CREATE MODEL for every variant (BigQuery ML, async)
    python -m app.forecast.pipeline forecast    # bt_forecasts (backtest) and the contract `forecasts` table
    python -m app.forecast.pipeline recommend   # the contract `recommendations` table (reason text by Gemini)

Models are trained once, ahead of time (build plan 7.4); the demo only reads the stored tables.
"""
from __future__ import annotations

import argparse
import datetime as dt
import time

import pandas as pd

from . import bqio, params
from .series import build_series, estimate_ask_rates

SERIES_SCHEMA_FIELDS = [
    ("date", "DATE"), ("store_id", "STRING"), ("sku", "STRING"), ("category", "STRING"), ("qty_sold", "FLOAT64"),
    ("is_stockout", "BOOL"), ("unmet_signals", "FLOAT64"), ("ask_rate_hat", "FLOAT64"), ("y_a", "FLOAT64"),
    ("y_b", "FLOAT64"), ("y_b_rate_x0_5", "FLOAT64"), ("y_b_rate_x1_5", "FLOAT64"),
]
# (table, cutoff kind, variants trained on it)  variant -> (series column)
CUTOFFS = {"bt": "fc_series_bt", "prod": "fc_series_prod"}
VARIANTS = {
    "bt": {"a": "y_a", "b": "y_b", "b_rate_x0_5": "y_b_rate_x0_5", "b_rate_x1_5": "y_b_rate_x1_5"},
    "prod": {"a": "y_a", "b": "y_b"},
}


def cutoff_dates(c) -> dict[str, dt.date]:
    d0, d1 = bqio.data_span(c)
    return {"bt": d0 + dt.timedelta(days=params.BACKTEST_TRAIN_DAYS - 1), "prod": d1}


def model_name(kind: str, variant: str) -> str:
    return f"m_{kind}_{variant}"


def build_tables(c) -> dict[str, pd.DataFrame]:
    """Training series (A, B and the two sensitivity variants of B) and the ask-rate estimates per cutoff."""
    from google.cloud import bigquery

    cuts, rates_all = cutoff_dates(c), []
    series_out = {}
    for kind, table in CUTOFFS.items():
        facts = bqio.load_facts(c, cuts[kind])
        rates = estimate_ask_rates(facts)
        s = build_series(facts, rates)
        for name, factor in params.SENSITIVITY_FACTORS.items():
            s[f"y_{name}"] = build_series(facts, rates, factor)["y_b"]
        schema = [bigquery.SchemaField(n, t) for n, t in SERIES_SCHEMA_FIELDS]
        out = s[[n for n, _ in SERIES_SCHEMA_FIELDS]].copy()
        out["date"] = out["date"].dt.date  # DATE column: no time part
        bqio.load_rows(c, table, out, schema=schema)
        rates.insert(0, "cutoff", cuts[kind])
        rates.insert(0, "kind", kind)
        rates_all.append(rates)
        series_out[kind] = s
        print(f"  {table}: {len(s):,} rows (cutoff {cuts[kind]}); extra unmet units in B: "
              f"{(s['y_b'] - s['y_a']).sum():.1f}")
    est = pd.concat(rates_all, ignore_index=True)
    bqio.load_rows(c, "ask_rate_estimates", est, schema=[
        bigquery.SchemaField("kind", "STRING"), bigquery.SchemaField("cutoff", "DATE"),
        bigquery.SchemaField("category", "STRING"), bigquery.SchemaField("ask_rate_hat", "FLOAT64"),
        bigquery.SchemaField("signals", "FLOAT64"), bigquery.SchemaField("expected_unmet", "FLOAT64"),
        bigquery.SchemaField("source", "STRING")])
    return series_out


def create_model_sql(kind: str, variant: str, column: str) -> str:
    F = bqio.fq()
    return f"""CREATE OR REPLACE MODEL {F}.{model_name(kind, variant)}
OPTIONS (model_type = 'ARIMA_PLUS', time_series_timestamp_col = 'date', time_series_data_col = 'y',
         time_series_id_col = ['store_id', 'sku'], horizon = {params.HORIZON_DAYS}, auto_arima = TRUE,
         data_frequency = 'DAILY', holiday_region = 'ID')
AS SELECT date, store_id, sku, {column} AS y FROM {F}.{CUTOFFS[kind]}"""


def train_all(c, only: list[str] | None = None) -> None:
    """Submit every CREATE MODEL at once (BigQuery runs them in parallel) and wait for all."""
    jobs = {}
    for kind, variants in VARIANTS.items():
        for variant, column in variants.items():
            name = model_name(kind, variant)
            if only and name not in only:
                continue
            jobs[name] = c.query(create_model_sql(kind, variant, column))
            print(f"  submitted {name}")
    start = time.time()
    pending = dict(jobs)
    while pending:
        time.sleep(20)
        for name, job in list(pending.items()):
            job.reload()
            if job.state == "DONE":
                pending.pop(name)
                print(f"  {name}: {'FAILED ' + str(job.error_result) if job.error_result else 'done'} "
                      f"after {time.time() - start:.0f}s", flush=True)
    print(f"all models finished in {time.time() - start:.0f}s")


def _forecast_select(kind: str, variant: str, label: str) -> str:
    """ML.FORECAST of one model as rows (negative demand clipped to 0): variant, store, SKU, day, qty, interval."""
    F = bqio.fq()
    return (f"SELECT '{label}' AS variant, store_id, sku, DATE(forecast_timestamp) AS forecast_date, "
            f"GREATEST(0.0, forecast_value) AS forecast_qty, GREATEST(0.0, prediction_interval_lower_bound) AS lower, "
            f"GREATEST(0.0, prediction_interval_upper_bound) AS upper "
            f"FROM ML.FORECAST(MODEL {F}.{model_name(kind, variant)}, "
            f"STRUCT({params.HORIZON_DAYS} AS horizon, {params.INTERVAL_CONFIDENCE} AS confidence_level))")


def forecast_all(c) -> dt.date:
    """Backtest forecasts of every variant -> bt_forecasts; production A and B -> the contract `forecasts` table."""
    F = bqio.fq()
    bt = " UNION ALL ".join(_forecast_select("bt", v, v) for v in VARIANTS["bt"])
    bqio.execute(c, f"CREATE OR REPLACE TABLE {F}.bt_forecasts AS {bt}")
    run_date = cutoff_dates(c)["prod"] + dt.timedelta(days=1)   # the forecast is made the morning after the last data day
    bqio.execute(c, f"DELETE FROM {F}.forecasts WHERE run_date = DATE '{run_date}'")
    prod = " UNION ALL ".join(_forecast_select("prod", v, v.upper()) for v in VARIANTS["prod"])
    bqio.execute(c, f"INSERT INTO {F}.forecasts (run_date, store_id, sku, model, forecast_date, forecast_qty, lower, upper) "
                    f"SELECT DATE '{run_date}', store_id, sku, variant, forecast_date, forecast_qty, lower, upper FROM ({prod})")
    return run_date


def calendar_context(run_date: dt.date) -> dict:
    """Calendar hint for the reason text, only when the payday window (day 25 to day 5) starts inside the days the
    order covers; later events say nothing about this order."""
    for i in range(params.COVER_DAYS):
        d = run_date + dt.timedelta(days=i)
        if d.day == 25:
            return {"calendar": f"a payday window starts in {i} days (on {d.isoformat()}), inside the days this order covers"}
    return {}


def recommend_all(c, use_llm: bool = True) -> tuple[pd.DataFrame, dict]:
    """Read the latest forecasts, build one recommendation row per store and SKU, write them to `recommendations`."""
    from .reason import add_reason_text
    from .recommend import build_recommendations

    F = bqio.fq()
    last_day = cutoff_dates(c)["prod"]
    run_date = last_day + dt.timedelta(days=1)
    facts = bqio.load_facts(c, last_day)
    fcs = bqio.query(c, f"SELECT store_id, sku, model, forecast_date, forecast_qty, lower, upper FROM {F}.forecasts "
                        f"WHERE run_date = @run", {"run": run_date})
    if fcs.empty:
        raise SystemExit(f"no forecasts for run_date {run_date}: run `forecast` first")
    stock = bqio.query(c, f"SELECT store_id, sku, closing_stock AS on_hand FROM {F}.stock_events WHERE date = @d",
                       {"d": last_day})
    products = bqio.query(c, f"SELECT sku, name, price_idr, shelf_life_days FROM {F}.product_master WHERE is_carried")
    rates = bqio.query(c, f"SELECT category, ask_rate_hat FROM {F}.ask_rate_estimates WHERE kind = 'prod'")
    df = build_recommendations(facts, fcs, stock, products, rates, run_date)
    client = model = None
    if use_llm:
        from ..config import settings
        from ..extract.client import make_client

        client, model = make_client(settings.gcp_project, settings.gcp_location), settings.gemini_model
    df, stats = add_reason_text(df, dict(zip(products["sku"], products["name"])), calendar_context(run_date),
                                client=client, model=model)
    bqio.execute(c, f"DELETE FROM {F}.recommendations WHERE run_date = DATE '{run_date}'")
    schema = c.get_table(f"{bqio.settings.gcp_project}.{bqio.settings.bq_dataset}.recommendations").schema
    bqio.load_rows(c, "recommendations", df, schema=schema, truncate=False)
    return df, stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=["series", "train", "forecast", "recommend"])
    ap.add_argument("--no-llm", action="store_true", help="recommend: use the template reason text only")
    ap.add_argument("--only", nargs="*", help="model names, e.g. m_bt_a m_prod_b")
    args = ap.parse_args()
    c = bqio.client()
    if args.step == "series":
        build_tables(c)
    elif args.step == "train":
        train_all(c, args.only)
    elif args.step == "forecast":
        print("forecasts written for run_date", forecast_all(c))
    elif args.step == "recommend":
        df, stats = recommend_all(c, use_llm=not args.no_llm)
        print(f"{len(df)} recommendation rows, {int(df['risk_type'].notna().sum())} flagged; reason text: {stats}")
        print(df["risk_type"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
