# API contract (v0, scaffold)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness + active backend/model |
| POST | `/api/shopper/chat` | `{session_id, store_id, message}` -> `{session_id, reply, signal, tool_calls[], error}` (see below) |
| POST | `/api/manager/chat` | `{session_id, message, store_id, sku?}` -> `{session_id, reply, citations[], unverified_numbers[], tool_calls[], error}` (see below) |
| GET | `/api/skus?store_id=` | SKU list with risk flag and reorder A vs B |
| GET | `/api/skus/{sku}?store_id=` | History + forecast A/B + recent signals |
| GET | `/api/gaps?store_id=` | Assortment gaps by category |
| GET | `/api/signals/recent?limit=` | Latest extracted signals (fallback for Firestore) |
| GET | `/api/experiment` | Simulation experiment results |
| POST | `/api/demo/reset` | Reset the demo sandbox |
| POST | `/internal/pubsub/push` | Pub/Sub push endpoint (extractor) |

Response shapes other than `/api/health`, `/api/shopper/chat` and `/api/manager/chat` are placeholders until implemented.

## `POST /api/shopper/chat`

- Request: `session_id` (1-128 chars, one per conversation), `store_id` (default `S01`, 404 if unknown),
  `message` (1-1000 chars).
- Response: `reply` (Bahasa Indonesia, max 3 sentences), `tool_calls` (`[{name, args}]` of this turn),
  `signal` = `{conversation_id, turn, logged}` where `logged` says the turn was published for signal
  extraction (the extractor runs asynchronously, so no extracted signal is returned here), `error`
  (null, or an error class name when the model failed and `reply` is a generic apology; HTTP status stays 200).
- Stock, price and shelf location in `reply` come only from tool results. A reply containing a price or
  stock count that no tool returned is replaced by a safe fallback sentence.
- Every turn is published automatically as a `ConversationEvent` (`app/signals/publisher.py`):
  `{conversation_id, turn, ts, store_id, channel, transcript[], tool_calls[]}`. Consumers keep the latest
  turn per `conversation_id`.

## `POST /api/manager/chat`

- Request: `session_id`, `message` (1-1000 chars), `store_id` (default `S01`), `sku` (optional: the SKU on screen;
  both are passed to the agent as a context line on every turn, so the store can change mid-conversation).
- `reply` is in the language of the question. Numbers and claims carry evidence markers like `[E3]` or `[E1, E2]`.
- `citations`: the evidence items the reply cites (unknown ids are stripped from the reply; if the model cites
  nothing, all evidence it looked at this turn is returned). Ids are unique within a session. Shapes:
  - `{type: "sku", id, store_id, sku, name, on_hand, sold_7d, stockout_days_7d, unmet_signals_7d, est_unmet_units_7d,
    forecast_a_7d?, forecast_b_7d?, recommended_qty_a?, recommended_qty_b?, risk_type?, lost_revenue_idr?}`
  - `{type: "signal", id, store_id, sku, date, quote, outcome, conversation_id}` (a shopper request, verbatim)
  - `{type: "gap", id, store_id, normalized_name, requests_28d, requests_total, quotes[]}`
  - `{type: "query", id, sql, row_count}` (free-form SQL the agent ran)
- `unverified_numbers`: numbers of 2+ digits in the reply that no tool returned (and the user did not write). The
  reply is not altered; the UI may flag it.
- `tool_calls`: `[{name, args, status}]` for the turn.
- Forecast-based fields (`forecast_*`, `recommended_qty_*`, `risk_type`) are null until the `recommendations` table is
  populated. Until then the agent states that forecasts are not available and reports observed facts only.
- `query_data` is read-only: one `SELECT` over the `v_*` views (parsed with sqlglot, `LIMIT 100` forced, BigQuery
  dry run checks statement type, referenced tables and bytes, `maximum_bytes_billed` 100 MB, 30 s timeout). Set
  `AGENT_SQL_SA` to run it as a service account that can read only those views.
