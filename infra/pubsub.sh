#!/usr/bin/env bash
# Create the conversations topic and an OIDC-authenticated push subscription straight to Cloud Run
# (not through Firebase Hosting). The API rejects pushes without a valid token (401).
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
REGION="${GCP_LOCATION:-us-central1}"
NUMBER="$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
API_URL="${API_URL:-https://demand-radar-api-$NUMBER.$REGION.run.app}"  # must equal PUBSUB_AUDIENCE in deploy.sh
INVOKER="dr-pubsub-invoker@$GCP_PROJECT.iam.gserviceaccount.com"

gcloud pubsub topics create conversations --project "$GCP_PROJECT" || true
gcloud pubsub subscriptions create conversations-extractor --project "$GCP_PROJECT" \
  --topic conversations --push-endpoint "$API_URL/pubsub/extract" \
  --push-auth-service-account "$INVOKER" --push-auth-token-audience "$API_URL" \
  --ack-deadline 60 --min-retry-delay 10s --max-retry-delay 300s || true
