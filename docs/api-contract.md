# API contract (v0, scaffold)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness + active backend/model |
| POST | `/api/shopper/chat` | `{session_id, store_id, message}` -> `{reply, signal}` |
| POST | `/api/manager/chat` | `{session_id, message, store_id, sku?}` -> `{reply, tool_calls[]}` |
| GET | `/api/skus?store_id=` | SKU list with risk flag and reorder A vs B |
| GET | `/api/skus/{sku}?store_id=` | History + forecast A/B + recent signals |
| GET | `/api/gaps?store_id=` | Assortment gaps by category |
| GET | `/api/signals/recent?limit=` | Latest extracted signals (fallback for Firestore) |
| GET | `/api/experiment` | Simulation experiment results |
| POST | `/api/demo/reset` | Reset the demo sandbox |
| POST | `/internal/pubsub/push` | Pub/Sub push endpoint (extractor) |

Response shapes are placeholders until the endpoints are implemented.
