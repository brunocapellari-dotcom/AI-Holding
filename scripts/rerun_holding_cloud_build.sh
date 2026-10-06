#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="ai-holding-prod-bc"
REGION="southamerica-east1"
TARGETS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/infra/gcp/holding-quality-targets.json"
BUILD_FILE="${HOME}/holding-cloud-builds.tsv"
REPO="${1:-}"

if [[ -z "${REPO}" ]]; then
  echo "usage: $0 <repository-name>" >&2
  exit 2
fi

branch="$(
  python3 - "${TARGETS}" "${REPO}" <<'PY'
import json
import sys

path, repo = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
for item in data["targets"]:
    if item["repo"] == repo:
        print(item["branch"])
        raise SystemExit(0)
raise SystemExit(3)
PY
)"

resource_name="$(printf '%s' "${REPO}" | tr '[:upper:]_' '[:lower:]-' | tr -cd 'a-z0-9-')"
trigger="holding-quality-${resource_name}"

build_id="$(
  gcloud builds triggers run "${trigger}"     --region="${REGION}"     --project="${PROJECT_ID}"     --branch="${branch}"     --format='value(metadata.build.id)'
)"

test -n "${build_id}"

tmp="$(mktemp)"
if [[ -f "${BUILD_FILE}" ]]; then
  awk -F '\t' -v repo="${REPO}" '$1 != repo' "${BUILD_FILE}" > "${tmp}"
fi
printf '%s\t%s\t%s\n' "${REPO}" "${branch}" "${build_id}" >> "${tmp}"
mv "${tmp}" "${BUILD_FILE}"

gcloud storage cp "${BUILD_FILE}"   "gs://${PROJECT_ID}-ai-execution-evidence/Holding/build-batches/latest.tsv" >/dev/null

echo "${REPO} restarted: ${build_id}"
