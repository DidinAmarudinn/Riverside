-- Demand Radar tables (contract: docs/api-contract.md §1). Replace ${PROJECT} / ${DATASET} before running.
CREATE SCHEMA IF NOT EXISTS `${PROJECT}.${DATASET}` OPTIONS (location = 'us-central1');

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.stores` (
  store_id STRING, name STRING, city STRING, lat FLOAT64, lng FLOAT64
);

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.product_master` (
  sku STRING, name STRING, brand STRING, category STRING,
  pack_size STRING, unit STRING, price_idr INT64, shelf_life_days INT64, aisle STRING,
  synonyms ARRAY<STRING>,
  is_carried BOOL             -- false = asked for but not sold (assortment gaps)
);

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.calendar_context` (
  date DATE, is_payday_window BOOL, is_holiday BOOL, holiday_name STRING,
  is_ramadan BOOL, is_lebaran_window BOOL, weather STRING
);

-- Simulation ground truth. Never exposed through a view or to the agents.
CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.true_demand` (
  date DATE, store_id STRING, sku STRING, demand_qty INT64
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.stock_events` (
  date DATE, store_id STRING, sku STRING,
  opening_stock INT64, received_qty INT64, closing_stock INT64, is_stockout BOOL
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.pos_sales` (
  date DATE, store_id STRING, sku STRING, qty_sold INT64, revenue_idr INT64  -- qty_sold = min(demand, stock)
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.conversations` (
  conversation_id STRING, store_id STRING, ts TIMESTAMP, channel STRING, transcript STRING,
  gt_sku STRING, gt_outcome STRING  -- ground truth for scoring extraction only; never in a view
) PARTITION BY DATE(ts);

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.demand_signals` (
  signal_id STRING, conversation_id STRING,
  sandbox_id STRING,          -- null for historical data, set for live demo signals
  store_id STRING, ts TIMESTAMP, date DATE,
  requested_text STRING, sku STRING, normalized_name STRING, category STRING,
  outcome STRING,             -- purchased | out_of_stock | not_carried | substituted | low_confidence
  substitute_sku STRING, qty INT64, confidence FLOAT64, model_version STRING
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.forecasts` (
  run_date DATE, store_id STRING, sku STRING,
  model STRING,               -- A = POS only, B = POS + unmet demand
  forecast_date DATE, forecast_qty FLOAT64, lower FLOAT64, upper FLOAT64
) PARTITION BY run_date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.recommendations` (
  run_date DATE, store_id STRING, sku STRING, on_hand INT64,
  forecast_a_7d FLOAT64, forecast_b_7d FLOAT64, unmet_7d INT64,
  recommended_qty_a INT64, recommended_qty_b INT64,
  risk_type STRING,           -- stockout_risk | overstock | unmet_spike | null
  lost_revenue_idr INT64, reason_text STRING
) PARTITION BY run_date CLUSTER BY store_id, sku;
