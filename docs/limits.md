# Limits and quotas

Project `riverside-511503`, region `us-central1`. Checked 2026-10-14.

## Gemini on Vertex AI

- Model: `gemini-2.5-flash`, regional endpoint `us-central1` (verified, HTTP 200).
- Gemini 2.x on Vertex AI uses **dynamic shared quota**: there is no fixed requests-per-minute number per project.
  Capacity is shared across all customers in the region, so a burst can return `429 RESOURCE_EXHAUSTED` at any time.
- Consequences for our code:
  - Every Gemini call retries on 429/503 with exponential backoff and jitter.
  - Batch jobs (synthetic conversations, historical extraction) run with bounded concurrency (start at 4–8 parallel calls).
  - Demo-critical answers (scenario buttons, hero scenario) are cached, with a stored fallback if Gemini times out (20 s).
- If 429s persist, fall back to the `global` endpoint (`GCP_LOCATION=global`) for Gemini only.

## BigQuery ML

- `ARIMA_PLUS` with `holiday_region='ID'` trains in `us-central1` (verified).
- `AI.FORECAST` (TimesFM) validates in `us-central1` and `US` (dry run).
- Create the `demand_radar` dataset in `us-central1`, same as Firestore and Cloud Run.

## Cost guard

- Budget alert: Rp500.000 (~US$30) at 50/90/100% on the project's billing account.
- Agent SQL queries set `maximum_bytes_billed`.
