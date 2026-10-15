-- Read-only views for the manager agent (contract: docs/api-contract.md §1).
-- Rules: never read true_demand, never select gt_sku / gt_outcome, base data only (sandbox_id IS NULL).
-- Grant dr-agent-sql@ BigQuery Data Viewer on these views only.

-- One signal per conversation. The extractor's own rows win over the gt_bootstrap seed; among
-- extractor versions the newest model_version wins. Base data only (sandbox_id IS NULL).
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_signals` AS
SELECT * EXCEPT (rn) FROM (
  SELECT s.*,
         ROW_NUMBER() OVER (
           PARTITION BY conversation_id
           ORDER BY (model_version = 'gt_bootstrap'), model_version DESC
         ) AS rn
  FROM `${PROJECT}.${DATASET}.demand_signals` s
  WHERE sandbox_id IS NULL
)
WHERE rn = 1;

-- Unmet demand per day: shoppers who asked but could not buy (confident signals only).
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_unmet_daily` AS
SELECT date, store_id, sku, normalized_name, category, outcome, SUM(qty) AS unmet_qty, COUNT(*) AS requests
FROM `${PROJECT}.${DATASET}.v_signals`
WHERE outcome IN ('out_of_stock', 'not_carried')
GROUP BY date, store_id, sku, normalized_name, category, outcome;

-- Latest recommendation per SKU per store, with product details.
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_sku_summary` AS
SELECT r.*, p.name, p.brand, p.category, p.pack_size, p.price_idr, p.shelf_life_days, p.aisle
FROM `${PROJECT}.${DATASET}.recommendations` r
JOIN `${PROJECT}.${DATASET}.product_master` p USING (sku)
WHERE r.run_date = (SELECT MAX(run_date) FROM `${PROJECT}.${DATASET}.recommendations`);

-- Products shoppers ask for that the store does not carry.
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_assortment_gaps` AS
SELECT store_id, category, normalized_name, COUNT(*) AS requests,
       MIN(date) AS first_seen, MAX(date) AS last_seen
FROM `${PROJECT}.${DATASET}.v_signals`
WHERE outcome = 'not_carried'
GROUP BY store_id, category, normalized_name;

-- Conversation quotes behind each signal (the evidence drawer). No ground-truth columns.
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_evidence` AS
SELECT s.store_id, s.sku, s.date, s.ts, s.outcome, s.requested_text, s.confidence,
       c.conversation_id, c.channel, c.transcript
FROM `${PROJECT}.${DATASET}.v_signals` s
JOIN `${PROJECT}.${DATASET}.conversations` c USING (conversation_id)
WHERE s.outcome != 'low_confidence';

-- Revenue lost on the latest day with signals: unmet demand x price.
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.v_lost_revenue_today` AS
SELECT u.store_id, u.sku, p.name, u.unmet_qty, p.price_idr, u.unmet_qty * p.price_idr AS lost_revenue_idr
FROM `${PROJECT}.${DATASET}.v_unmet_daily` u
JOIN `${PROJECT}.${DATASET}.product_master` p USING (sku)
WHERE u.outcome = 'out_of_stock'
  AND u.date = (SELECT MAX(date) FROM `${PROJECT}.${DATASET}.v_signals`);
