#!/usr/bin/env bash
# Create the conversations topic and a push subscription to the API's extractor endpoint.
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}" "${API_URL:?set API_URL (Cloud Run URL)}"
gcloud pubsub topics create conversations --project "$GCP_PROJECT" || true
gcloud pubsub subscriptions create conversations-extractor --project "$GCP_PROJECT" \
  --topic conversations --push-endpoint "$API_URL/internal/pubsub/push" || true
