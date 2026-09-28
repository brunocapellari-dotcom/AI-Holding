#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ID="${PROJECT_ID:-ai-holding-prod-bc}"
export REGION="${REGION:-southamerica-east1}"
export GCP_GITHUB_CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
export MANIFEST="${ROOT_DIR}/infra/gcp/holding-shared-projects.json"

echo "============================================================"
echo " HOLDING SHARED GCP EXECUTION"
echo " project: ${PROJECT_ID}"
echo " region:  ${REGION}"
echo " AgroLog: EXCLUDED (dedicated GCP project)"
echo "============================================================"

gcloud config set project "${PROJECT_ID}" >/dev/null

python3 - "${MANIFEST}" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
repos = [item["repo"] for item in data["projects"]]
if "AgroLogMT" in repos:
    raise SystemExit("SAFETY ERROR: AgroLogMT must not be provisioned in the Holding shared GCP project")
if len(repos) != 11:
    raise SystemExit(f"expected 11 Holding-shared repositories, found {len(repos)}")
print("Holding repositories:", ", ".join(repos))
PY

bash "${ROOT_DIR}/scripts/bootstrap_gcp_execution_fabric.sh"

cat <<EOF

HOLDING SHARED FOUNDATION READY

The following 11 repositories are linked to Cloud Build in ${PROJECT_ID}.
AgroLogMT remains isolated in its existing dedicated GCP project.

You can close Cloud Shell after this succeeds.
Project-specific Cloud Build configs and triggers can be completed from the repositories without changing this shared foundation.
EOF
