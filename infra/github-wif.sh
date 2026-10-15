#!/usr/bin/env bash
# One-time setup so GitHub Actions can deploy without a service account key (Workload Identity Federation).
# Usage: GCP_PROJECT=riverside-511503 infra/github-wif.sh   (requires gcloud with Owner on the project)
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
REPO="${GITHUB_REPO:-DidinAmarudinn/Riverside}"
NUMBER="$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
SA="dr-deployer@$GCP_PROJECT.iam.gserviceaccount.com"

gcloud services enable sts.googleapis.com iamcredentials.googleapis.com --project "$GCP_PROJECT"

gcloud iam service-accounts describe "$SA" --project "$GCP_PROJECT" >/dev/null 2>&1 ||
  gcloud iam service-accounts create dr-deployer --project "$GCP_PROJECT" --display-name "GitHub Actions deployer"

# What infra/deploy.sh needs: Cloud Build + Artifact Registry + Cloud Run, Hosting and Firestore rules.
for role in run.admin cloudbuild.builds.editor artifactregistry.writer storage.admin viewer \
  firebasehosting.admin firebaserules.admin serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT" --member "serviceAccount:$SA" \
    --role "roles/$role" --condition None --quiet >/dev/null
done
# Deploy runs as dr-api; Cloud Build runs as the default compute SA.
for target in "dr-api@$GCP_PROJECT.iam.gserviceaccount.com" "$NUMBER-compute@developer.gserviceaccount.com"; do
  gcloud iam service-accounts add-iam-policy-binding "$target" --project "$GCP_PROJECT" \
    --member "serviceAccount:$SA" --role roles/iam.serviceAccountUser --quiet >/dev/null
done

gcloud iam workload-identity-pools describe github --project "$GCP_PROJECT" --location global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create github --project "$GCP_PROJECT" --location global \
    --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe github-oidc --project "$GCP_PROJECT" --location global \
  --workload-identity-pool github >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc github-oidc --project "$GCP_PROJECT" --location global \
    --workload-identity-pool github --display-name "GitHub OIDC" \
    --issuer-uri https://token.actions.githubusercontent.com \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition "assertion.repository=='$REPO'"

gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$GCP_PROJECT" \
  --role roles/iam.workloadIdentityUser --quiet >/dev/null \
  --member "principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"

echo "workload_identity_provider: projects/$NUMBER/locations/global/workloadIdentityPools/github/providers/github-oidc"
echo "service_account: $SA"
