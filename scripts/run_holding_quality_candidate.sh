#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
TRIGGER="${QUALITY_TRIGGER:-ai-holding-quality-manual}"
SHA="${1:-}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or gcloud project first" >&2
  exit 2
fi
if [[ -z "${SHA}" ]]; then
  echo "usage: $0 <COMMIT_SHA>" >&2
  exit 2
fi

BUILD_ID="$(
  gcloud builds triggers run "${TRIGGER}"     --region="${REGION}"     --project="${PROJECT_ID}"     --sha="${SHA}"     --format='value(metadata.build.id)'
)"

if [[ -z "${BUILD_ID}" ]]; then
  echo "ERROR: Cloud Build did not return a build id" >&2
  exit 3
fi

echo "quality build id: ${BUILD_ID}"
gcloud builds log --stream "${BUILD_ID}"   --region="${REGION}"   --project="${PROJECT_ID}" || true

STATUS="$(
  gcloud builds describe "${BUILD_ID}"     --region="${REGION}"     --project="${PROJECT_ID}"     --format='value(status)'
)"

if [[ "${STATUS}" != "SUCCESS" ]]; then
  echo "quality gate failed: ${STATUS}" >&2
  exit 4
fi

cat <<EOF

QUALITY GATE PASSED
commit: ${SHA}
build:  ${BUILD_ID}

This is the canonical CI evidence for the zero-cost path.
No production deployment or persistent Artifact Registry image was created.
EOF
