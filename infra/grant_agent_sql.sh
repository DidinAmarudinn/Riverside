#!/usr/bin/env bash
# Let the manager agent's SQL service account read ONLY the Demand Radar views.
#
#   GCP_PROJECT=riverside-511503 infra/grant_agent_sql.sh
#
# 1. Grants dataViewer on each allow-listed view (not on the dataset, so base tables such as true_demand and
#    conversations.gt_* stay unreadable for the account).
# 2. Authorizes those views on the dataset, so they can read the base tables on the caller's behalf.
# Safe to re-run. Needs Owner / BigQuery Admin. Keep this list in sync with ALLOWED_VIEWS in
# services/api/app/tools/sqlguard.py.
set -euo pipefail
: "${GCP_PROJECT:?set GCP_PROJECT}"
DATASET="${BQ_DATASET:-demand_radar}"
SA="${AGENT_SQL_SA:-dr-agent-sql@${GCP_PROJECT}.iam.gserviceaccount.com}"
VIEWS=(v_sku_summary v_evidence v_assortment_gaps v_lost_revenue_today v_unmet_daily v_signals)

for v in "${VIEWS[@]}"; do
  echo "grant dataViewer on ${DATASET}.${v} to ${SA}"
  bq add-iam-policy-binding --project_id="$GCP_PROJECT" \
    --member="serviceAccount:${SA}" --role="roles/bigquery.dataViewer" \
    "${GCP_PROJECT}:${DATASET}.${v}" > /dev/null
done

TMP="$(mktemp -d)"
bq show --project_id="$GCP_PROJECT" --format=prettyjson "${GCP_PROJECT}:${DATASET}" > "${TMP}/dataset.json"
cp "${TMP}/dataset.json" "${TMP}/dataset.backup.json"
python3 - "${TMP}/dataset.json" "$GCP_PROJECT" "$DATASET" "${VIEWS[@]}" <<'PY'
import json, sys
path, project, dataset, *views = sys.argv[1:]
d = json.load(open(path))
access = d.setdefault("access", [])
have = {(a["view"]["tableId"]) for a in access if "view" in a}
added = []
for v in views:
    if v not in have:
        access.append({"view": {"projectId": project, "datasetId": dataset, "tableId": v}})
        added.append(v)
json.dump(d, open(path, "w"), indent=2)
print("authorized views added:", added or "none (already present)")
PY
bq update --project_id="$GCP_PROJECT" --source "${TMP}/dataset.json" "${GCP_PROJECT}:${DATASET}"
echo "done. previous dataset access list saved at ${TMP}/dataset.backup.json"
