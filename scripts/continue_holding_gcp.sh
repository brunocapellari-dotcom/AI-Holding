#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export PROJECT_ID

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or gcloud project first" >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree must be clean before proving a release candidate" >&2
  exit 3
fi

SHA="${1:-$(git rev-parse HEAD)}"
test -n "${SHA}"

echo "== bootstrap canonical GCP execution fabric =="
bash scripts/bootstrap_gcp_execution_fabric.sh

echo "== configure separated Holding manual gates =="
bash scripts/activate_holding_gcp_triggers.sh

echo "== run exact-SHA Holding quality candidate =="
bash scripts/run_holding_quality_candidate.sh "${SHA}"
