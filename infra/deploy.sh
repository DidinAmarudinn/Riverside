#!/usr/bin/env bash
# Usage: infra/deploy.sh [api|web|all]   (requires gcloud + firebase CLI, and GCP_PROJECT set)
# Deploy the API first: Hosting refuses the /api/** rewrite until the Cloud Run service exists.
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
REGION="${GCP_LOCATION:-us-central1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

deploy_api() {
  local number repo image
  number="$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
  repo="$REGION-docker.pkg.dev/$GCP_PROJECT/demand-radar"
  image="$repo/api:$(git -C "$ROOT" rev-parse --short HEAD)"
  gcloud artifacts repositories describe demand-radar --project "$GCP_PROJECT" --location "$REGION" >/dev/null 2>&1 ||
    gcloud artifacts repositories create demand-radar --project "$GCP_PROJECT" --location "$REGION" \
      --repository-format docker --description "Demand Radar images"
  gcloud builds submit "$ROOT" --project "$GCP_PROJECT" \
    --config "$ROOT/infra/cloudbuild.yaml" --substitutions "_IMAGE=$image"
  # One warm instance keeps the first kiosk turn and the live signal under the < 5 s target (no cold start).
  # PUBLISHER=pubsub sends kiosk turns to the conversations topic (infra/pubsub.sh); the default is in-memory.
  gcloud run deploy demand-radar-api --project "$GCP_PROJECT" --region "$REGION" \
    --image "$image" --allow-unauthenticated \
    --service-account "dr-api@$GCP_PROJECT.iam.gserviceaccount.com" \
    --min-instances "${MIN_INSTANCES:-1}" --max-instances "${MAX_INSTANCES:-3}" \
    --set-env-vars "GCP_PROJECT=$GCP_PROJECT,GCP_LOCATION=$REGION,DATA_BACKEND=gcp,GOOGLE_GENAI_USE_VERTEXAI=TRUE,PUBLISHER=pubsub,PUBSUB_AUDIENCE=https://demand-radar-api-$number.$REGION.run.app"
}
deploy_web() {
  (cd "$ROOT/apps/web" && npm ci && npm run build)
  (cd "$ROOT" && firebase deploy --project "$GCP_PROJECT" --only hosting,firestore:rules)
}

case "${1:-all}" in
  api) deploy_api ;;
  web) deploy_web ;;
  all) deploy_api; deploy_web ;;
  *) echo "usage: $0 [api|web|all]"; exit 1 ;;
esac
