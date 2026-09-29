#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?PROJECT_ID is required}"
: "${REGION:?REGION is required}"
: "${SERVICE_NAME:?SERVICE_NAME is required}"
: "${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"
: "${IMAGE_REF:?IMAGE_REF is required}"

PMO_SERVICE_ACCOUNT="${PMO_SERVICE_ACCOUNT:-holding-pmo-worker@${PROJECT_ID}.iam.gserviceaccount.com}"
KNOWLEDGE_SERVICE_ACCOUNT="${KNOWLEDGE_SERVICE_ACCOUNT:-holding-knowledge-worker@${PROJECT_ID}.iam.gserviceaccount.com}"
MIGRATION_SERVICE_ACCOUNT="${MIGRATION_SERVICE_ACCOUNT:-holding-db-migration@${PROJECT_ID}.iam.gserviceaccount.com}"
SCHEDULER_SERVICE_ACCOUNT="${SCHEDULER_SERVICE_ACCOUNT:-holding-worker-scheduler@${PROJECT_ID}.iam.gserviceaccount.com}"
TF_BIN="${TF_BIN:-terraform}"
TF_DIR="${TF_DIR:-infra/terraform}"

plan_has_delete() {
  local plan_file="$1"
  local json_file
  json_file="$(mktemp)"
  "${TF_BIN}" -chdir="${TF_DIR}" show -json "${plan_file}" > "${json_file}"
  python3 - "${json_file}" <<'PY'
from __future__ import annotations

import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
for change in data.get("resource_changes", []):
    actions = ((change.get("change") or {}).get("actions") or [])
    if "delete" in actions:
        raise SystemExit(
            "destructive Terraform action rejected: "
            + str(change.get("address", "<unknown>"))
            + " -> "
            + ",".join(actions)
        )
PY
  rm -f "${json_file}"
}

echo "== initialize production Terraform state =="
"${TF_BIN}" -chdir="${TF_DIR}" init   -backend-config="bucket=${TF_STATE_BUCKET}"   -backend-config="prefix=control-plane/prod"

echo "== preserve/complete database foundation =="
if "${TF_BIN}" -chdir="${TF_DIR}" state show google_sql_database_instance.postgres >/dev/null 2>&1; then
  echo "database foundation already exists"
else
  "${TF_BIN}" -chdir="${TF_DIR}" plan     -var-file=prod.tfvars     -var="deploy_service=false"     -target=google_sql_database_instance.postgres     -target=google_sql_database.holding     -target=google_sql_user.holding     -target=google_secret_manager_secret_version.database_url     -out=foundation.tfplan
  plan_has_delete foundation.tfplan
  "${TF_BIN}" -chdir="${TF_DIR}" apply -auto-approve foundation.tfplan
fi

echo "== recover stale Terraform taint only for known deployable runtime resources =="
for address in   'google_cloud_run_v2_service.api[0]'   'google_cloud_run_v2_job.migrate[0]'   'google_cloud_run_v2_job.bootstrap[0]'   'google_cloud_run_v2_job.pmo_worker[0]'   'google_cloud_run_v2_job.knowledge_worker[0]'   'google_cloud_run_v2_job.github_collector[0]'   'google_cloud_run_v2_job.cloud_build_collector[0]'   'google_cloud_run_v2_job.pmo_acceptance[0]'   'google_cloud_run_v2_job.knowledge_acceptance[0]'; do
  state="$("${TF_BIN}" -chdir="${TF_DIR}" state show "${address}" 2>/dev/null || true)"
  if printf '%s\n' "${state}" | head -n 1 | grep -q '(tainted)'; then
    "${TF_BIN}" -chdir="${TF_DIR}" untaint "${address}"
  fi
done

echo "== non-destructive production plan =="
"${TF_BIN}" -chdir="${TF_DIR}" plan   -var-file=prod.tfvars   -var="deploy_service=true"   -var="image_ref=${IMAGE_REF}"   -out=tfplan
plan_has_delete tfplan

echo "== apply with one bounded re-plan retry =="
set +e
"${TF_BIN}" -chdir="${TF_DIR}" apply -auto-approve tfplan
apply_status=$?
set -e
if [[ "${apply_status}" -ne 0 ]]; then
  sleep 30
  "${TF_BIN}" -chdir="${TF_DIR}" plan     -var-file=prod.tfvars     -var="deploy_service=true"     -var="image_ref=${IMAGE_REF}"     -out=tfplan-retry
  plan_has_delete tfplan-retry
  "${TF_BIN}" -chdir="${TF_DIR}" apply -auto-approve tfplan-retry
fi

echo "== database migrations =="
gcloud run jobs execute "${SERVICE_NAME}-migrate"   --project="${PROJECT_ID}"   --region="${REGION}"   --wait

echo "== bootstrap canonical portfolio and identities =="
gcloud run jobs execute "${SERVICE_NAME}-bootstrap"   --project="${PROJECT_ID}"   --region="${REGION}"   --wait

actual_pmo_subject="$(gcloud iam service-accounts describe "${PMO_SERVICE_ACCOUNT}"   --project="${PROJECT_ID}" --format='value(uniqueId)')"
expected_pmo_subject="$("${TF_BIN}" -chdir="${TF_DIR}" output -raw pmo_runtime_subject)"
test -n "${actual_pmo_subject}"
test "${actual_pmo_subject}" = "${expected_pmo_subject}"

actual_knowledge_subject="$(gcloud iam service-accounts describe "${KNOWLEDGE_SERVICE_ACCOUNT}"   --project="${PROJECT_ID}" --format='value(uniqueId)')"
expected_knowledge_subject="$("${TF_BIN}" -chdir="${TF_DIR}" output -raw knowledge_runtime_subject)"
test -n "${actual_knowledge_subject}"
test "${actual_knowledge_subject}" = "${expected_knowledge_subject}"

echo "== verify production IAM and schedulers =="
URL="$(gcloud run services describe "${SERVICE_NAME}"   --project="${PROJECT_ID}"   --region="${REGION}"   --format='value(status.url)')"
test -n "${URL}"

gcloud run services get-iam-policy "${SERVICE_NAME}"   --project="${PROJECT_ID}" --region="${REGION}" --format=json > /tmp/service-policy.json

python3 - /tmp/service-policy.json "${PMO_SERVICE_ACCOUNT}" "${KNOWLEDGE_SERVICE_ACCOUNT}" <<'PY'
from __future__ import annotations

import json
import sys

path, pmo, knowledge = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
bindings = data.get("bindings", [])
members = [m for b in bindings for m in b.get("members", [])]
if "allUsers" in members or "allAuthenticatedUsers" in members:
    raise SystemExit("public Cloud Run invocation is forbidden")

def has_invoker(email: str) -> bool:
    target = f"serviceAccount:{email}"
    return any(
        b.get("role") == "roles/run.invoker" and target in b.get("members", [])
        for b in bindings
    )

if not has_invoker(pmo):
    raise SystemExit("PMO service account is missing Cloud Run invoker")
if not has_invoker(knowledge):
    raise SystemExit("Knowledge service account is missing Cloud Run invoker")
PY

for job in "${SERVICE_NAME}-pmo-worker" "${SERVICE_NAME}-knowledge-worker" "${SERVICE_NAME}-cloud-build-collector"; do
  policy_file="/tmp/${job}-policy.json"
  gcloud run jobs get-iam-policy "${job}"     --project="${PROJECT_ID}" --region="${REGION}" --format=json > "${policy_file}"
  python3 - "${policy_file}" "${SCHEDULER_SERVICE_ACCOUNT}" <<'PY'
from __future__ import annotations

import json
import sys

path, scheduler = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
target = f"serviceAccount:{scheduler}"
if not any(
    b.get("role") == "roles/run.invoker" and target in b.get("members", [])
    for b in data.get("bindings", [])
):
    raise SystemExit("scheduler service account is missing job invoker")
PY
done

expected_migration_service_account="$("${TF_BIN}" -chdir="${TF_DIR}" output -raw migration_runtime_service_account)"
test "${expected_migration_service_account}" = "${MIGRATION_SERVICE_ACCOUNT}"

for scheduler in "${SERVICE_NAME}-pmo-schedule" "${SERVICE_NAME}-knowledge-schedule" "${SERVICE_NAME}-cloud-build-collector-schedule"; do
  scheduler_state="$(gcloud scheduler jobs describe "${scheduler}"     --project="${PROJECT_ID}" --location="${REGION}" --format='value(state)')"
  test "${scheduler_state}" = "ENABLED"
done

github_collector_job="$("${TF_BIN}" -chdir="${TF_DIR}" output -raw github_collector_job 2>/dev/null || true)"
if [[ -n "${github_collector_job}" ]]; then
  collector_state="$(gcloud scheduler jobs describe "${SERVICE_NAME}-github-collector-schedule"     --project="${PROJECT_ID}" --location="${REGION}" --format='value(state)')"
  test "${collector_state}" = "ENABLED"
fi

echo "== controlled PMO acceptance =="
gcloud run jobs execute "${SERVICE_NAME}-pmo-acceptance"   --project="${PROJECT_ID}" --region="${REGION}" --args=prepare --wait
gcloud run jobs execute "${SERVICE_NAME}-pmo-worker"   --project="${PROJECT_ID}" --region="${REGION}" --wait
gcloud run jobs execute "${SERVICE_NAME}-pmo-acceptance"   --project="${PROJECT_ID}" --region="${REGION}" --args=finalize --wait

echo "== controlled Knowledge acceptance =="
gcloud run jobs execute "${SERVICE_NAME}-knowledge-acceptance"   --project="${PROJECT_ID}" --region="${REGION}" --args=prepare --wait
gcloud run jobs execute "${SERVICE_NAME}-knowledge-worker"   --project="${PROJECT_ID}" --region="${REGION}" --wait
gcloud run jobs execute "${SERVICE_NAME}-knowledge-acceptance"   --project="${PROJECT_ID}" --region="${REGION}" --args=finalize --wait

python3 - "${IMAGE_REF}" "${URL}" > /workspace/release-summary.json <<'PY'
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

image_ref, service_url = sys.argv[1:]
print(
    json.dumps(
        {
            "accepted_at": datetime.now(UTC).isoformat(),
            "image_ref": image_ref,
            "service_url": service_url,
            "migration": "passed",
            "identity_checks": "passed",
            "scheduler_checks": "passed",
            "pmo_acceptance": "passed",
            "knowledge_acceptance": "passed",
            "cloud_build_supervision": "passed",
        },
        sort_keys=True,
    )
)
PY

echo "Production acceptance passed for ${IMAGE_REF}"
