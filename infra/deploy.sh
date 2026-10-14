#!/usr/bin/env bash
# Usage: infra/deploy.sh [api|web|all]   (requires gcloud + firebase CLI, and GCP_PROJECT set)
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
REGION="${GCP_LOCATION:-us-central1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

deploy_api() {
  IMAGE="gcr.io/$GCP_PROJECT/demand-radar-api"
  gcloud builds submit "$ROOT" --project "$GCP_PROJECT" \
    --config "$ROOT/infra/cloudbuild.yaml" --substitutions "_IMAGE=$IMAGE"
  gcloud run deploy demand-radar-api --project "$GCP_PROJECT" --region "$REGION" \
    --image "$IMAGE" --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT,DATA_BACKEND=gcp"
}
deploy_web() {
  (cd "$ROOT/apps/web" && npm ci && npm run build)
  (cd "$ROOT" && firebase deploy --project "$GCP_PROJECT" --only hosting,firestore)
}

case "${1:-all}" in
  api) deploy_api ;;
  web) deploy_web ;;
  all) deploy_api; deploy_web ;;
  *) echo "usage: $0 [api|web|all]"; exit 1 ;;
esac
