-- Seed demand_signals from conversation ground truth (model_version = 'gt_bootstrap') so the agent
-- views already hold data before the Langkah 4 extractor runs. Once the extractor writes its own
-- version for a conversation, v_signals (sql/02_views.sql) prefers that row over the seed.
--
-- requested_text comes from the first (shopper) turn of the JSON transcript. not_carried signals
-- keep sku = NULL (gt_sku is the NC-xxx catalog row); normalized_name drops the brand from the name.
DELETE FROM `${PROJECT}.${DATASET}.demand_signals` WHERE model_version = 'gt_bootstrap';

INSERT INTO `${PROJECT}.${DATASET}.demand_signals`
  (signal_id, conversation_id, sandbox_id, store_id, ts, date, requested_text, sku,
   normalized_name, category, outcome, substitute_sku, qty, confidence, model_version)
SELECT
  CONCAT('gt-', c.conversation_id),
  c.conversation_id,
  NULL,
  c.store_id,
  c.ts,
  DATE(c.ts, 'Asia/Jakarta'),
  JSON_VALUE(c.transcript, '$[0].text'),
  IF(c.gt_outcome = 'not_carried', NULL, c.gt_sku),
  LOWER(TRIM(REGEXP_REPLACE(
    IF(p.brand IS NULL OR p.brand = '', p.name, REPLACE(p.name, p.brand, '')), r'\s+', ' '))),
  p.category,
  c.gt_outcome,
  CAST(NULL AS STRING),
  1,
  1.0,
  'gt_bootstrap'
FROM `${PROJECT}.${DATASET}.conversations` c
LEFT JOIN `${PROJECT}.${DATASET}.product_master` p ON p.sku = c.gt_sku
WHERE c.gt_outcome != '';
