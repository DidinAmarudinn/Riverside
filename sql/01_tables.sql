-- Demand Radar tables. Replace ${PROJECT} / ${DATASET} before running (see infra/deploy.sh).
CREATE SCHEMA IF NOT EXISTS `${PROJECT}.${DATASET}`;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.product_master` (
  sku STRING, name STRING, brand STRING, category STRING, subcategory STRING,
  pack_size STRING, price_idr INT64, shelf_life_days INT64, perishable INT64, shelf_location STRING
);

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.true_demand` (
  date DATE, store_id STRING, sku STRING, true_units INT64
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.stock_events` (
  date DATE, store_id STRING, sku STRING,
  opening_stock INT64, received_units INT64, closing_stock INT64, stockout_flag INT64
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.pos_sales` (
  date DATE, store_id STRING, sku STRING, units_sold INT64, revenue_idr INT64
) PARTITION BY date CLUSTER BY store_id, sku;

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.conversations` (
  conversation_id STRING, ts TIMESTAMP, store_id STRING, channel STRING,
  transcript STRING, gt STRING  -- gt = hidden ground truth, simulation only
) PARTITION BY DATE(ts);

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.demand_signals` (
  signal_id STRING, conversation_id STRING, ts TIMESTAMP, store_id STRING,
  mentioned_text STRING, sku STRING, match_confidence FLOAT64,
  outcome STRING,            -- bought | out_of_stock | not_stocked | substituted
  qty INT64, substitute_sku STRING, requested_item STRING, category_guess STRING,
  extractor STRING
) PARTITION BY DATE(ts);
