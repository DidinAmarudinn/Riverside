# Architecture

```
Shopper (kiosk/chat) -> FastAPI (Cloud Run) -> Pub/Sub -> Signal extractor (Gemini structured output)
                                                              |-> BigQuery (demand_signals)
                                                              '-> Firestore (signals_live, read-only to the web app)
BigQuery ML (ARIMA_PLUS): forecast A (POS only) vs forecast B (POS + unmet demand)
Manager agent (ADK + Gemini) --tools--> BigQuery -> explainable reorder advice
```

Status: scaffold. See `README.md` for what is wired up.
