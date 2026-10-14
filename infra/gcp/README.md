# GCP Execution Fabric

Google Cloud is the canonical execution substrate for the AI ecosystem. GitHub remains the source/review surface, but project execution must not depend on GitHub-hosted runner credits.

## Execution model

- Pull-request and main-branch CI: Cloud Build.
- APIs and long-lived HTTP services: Cloud Run services.
- Batch, collectors, workers, evaluations and release gates: Cloud Run Jobs or Cloud Build when the workload is build/test-centric.
- Recurring schedules: Cloud Scheduler, not GitHub cron.
- Event fan-out: Pub/Sub; Cloud Tasks only when delivery semantics require it.
- Containers: Artifact Registry.
- Secrets: Secret Manager; no long-lived JSON service-account keys in repositories or runner disks.
- Structured transactional state: Cloud SQL PostgreSQL where appropriate.
- Analytics/domain warehouses: BigQuery where appropriate.
- Raw/evidence/backups/media: Cloud Storage.
- Observability: Cloud Logging, Monitoring and Trace.
- Heavy media/ML/GPU: on-demand only; do not keep GPU workers permanently allocated.

## Repositories

The canonical inventory is `ecosystem-projects.json`. The bootstrap links every repository to a single regional Cloud Build GitHub connection so private repositories can remain private.

## Security invariants

1. GitHub repository visibility must never be used as a workaround for runner capacity.
2. No static Google Cloud service-account key is stored in GitHub.
3. The Cloud Build GitHub App connection token is managed by Google in Secret Manager.
4. Each production runtime uses a dedicated service account and least privilege.
5. Builds write evidence to the dedicated GCS evidence bucket, not GitHub Actions artifacts.
6. Production data, vaults, raw ingested content, quarantine, database dumps and CONFIDENTIAL/RESTRICTED material never become repository content.
7. Scheduled production work is migrated away from GitHub Actions cron after the corresponding Cloud Scheduler/Cloud Run Job is verified.
8. GitHub Actions workflows remain only as temporary fallback until their GCP replacement has passed the whole-project gate.

## Bootstrap

From Cloud Shell in this repository:

```bash
bash scripts/bootstrap_gcp_execution_fabric.sh
```

The first run may stop with exit code 20 and print the Cloud Build GitHub App authorization URL. Authorize the app for the repositories, then run the script again. Google documents this browser authorization step as required for a 2nd-generation GitHub connection.

After every repository contains its approved `cloudbuild.yaml`, activate main-branch triggers:

```bash
bash scripts/activate_gcp_build_triggers.sh
```

Pull-request triggers and production schedules are added only after the project-specific full gate is translated and proven on Cloud Build. We do not disable the existing GitHub workflow before the GCP path produces equivalent or stronger evidence.


## Project release-candidate gates

Projects that are intentionally validating a branch ahead of `main` declare an
exact `candidate_branch` in `infra/gcp/ecosystem-projects.json`. This is
separate from the `main` trigger and does not promote anything to production.

Run a configured candidate with:

```bash
PROJECT_ID="${PROJECT_ID:-ai-holding-prod-bc}" \
  bash scripts/run_gcp_project_candidate.sh WHATSAPP_AI
```

The runner bootstraps the canonical execution fabric idempotently, verifies the
linked Cloud Build repository, creates an exact-branch trigger when absent,
starts the build, streams logs, and checks the final state.

For WHATSAPP_AI, the first successful bootstrap pass is intentionally expected
to end with `LOCKFILE_BLOCKER` / exit 42 when no committed `package-lock.json`
exists. The generated lockfile is stored by exact source commit. From an
up-to-date `WHATSAPP_AI` checkout on `build/final-foundation`:

```bash
PROJECT_ID="${PROJECT_ID:-ai-holding-prod-bc}" \
COMMIT_LOCKFILE=true \
PUSH_LOCKFILE=true \
  bash scripts/adopt-cloud-lockfile.sh
```

The adoption script fails closed unless the stored artifact belongs to exactly
the current Git `HEAD` and its root dependency contract matches `package.json`.
After the lockfile commit, rerun the candidate gate. Production promotion remains
blocked until the full project acceptance matrix and authorized live staging are green.

## Migration acceptance

A project is considered migrated only when:

- its deterministic whole-project gate passes in Cloud Build;
- its live/scheduled workloads run from Cloud Run Jobs/Scheduler where applicable;
- logs and evidence are durable in GCP;
- required secrets come from Secret Manager;
- the project can run with GitHub Actions hosted minutes set effectively to zero;
- rollback/re-run is documented and tested;
- no duplicate scheduler remains active.


## First proof for AI-Holding

Before enabling any permanent trigger, validate the final Holding branch directly from Cloud Shell:

```bash
git checkout holding-official-spec-2026-09-15
gcloud builds submit \
  --config=cloudbuild.yaml \
  --region=southamerica-east1 \
  --project="${PROJECT_ID}" \
  .
```

This build must pass the whole-project gate and persist its Gitleaks report, Trivy IaC report, CycloneDX SBOM, Trivy image report and image identifier under:

```text
gs://${PROJECT_ID}-ai-execution-evidence/AI-Holding/<BUILD_ID>/
```

Only after that proof is green should the permanent Cloud Build trigger be enabled for the repository. Production deployment/cutover remains blocked until the production acceptance matrix is also green. Existing GitHub-hosted workflows are not evidence of failure while they continue to terminate before allocating a runner.


## Fast continuation after GitHub App authorization

For the Holding itself, the normal continuation command is:

```bash
git checkout holding-official-spec-2026-09-15
bash scripts/continue_holding_gcp.sh
```

The script is fail-closed. It requires a clean working tree, bootstraps the execution fabric, creates the separated manual quality/release triggers, and executes the quality gate against the exact checked-out commit. If the GitHub App still needs browser authorization, the bootstrap stops with exit code 20 and prints the authorization URL; after authorization, run the same command again.

## Holding quality and release gates

After the GitHub App connection is complete, configure the Holding-only manual gates (quality is always created; candidate and release only with `ENABLE_PAID_GCP_DEPLOY=true`):

```bash
bash scripts/activate_holding_gcp_triggers.sh
```

The quality gate (`cloudbuild.yaml`) runs with the low-privilege `ai-build-executor` and persists nothing (zero recurring cost). The release-candidate gate (`cloudbuild.candidate.yaml`) runs the identical quality steps with the same `ai-build-executor`, then publishes provenance evidence; it requires Cloud Build approval. The release gate runs with the existing production deployer and additionally requires Cloud Build approval before execution.

For the current release candidate, use the exact Git commit rather than a mutable branch:

```bash
RC_SHA="$(git rev-parse HEAD)"

QUALITY_BUILD_ID="$(
  gcloud builds triggers run ai-holding-candidate-manual \
    --region=southamerica-east1 \
    --project="${PROJECT_ID}" \
    --sha="${RC_SHA}" \
    --format='value(metadata.build.id)'
)"

gcloud builds log --stream "${QUALITY_BUILD_ID}" \
  --region=southamerica-east1 \
  --project="${PROJECT_ID}"

test "$(
  gcloud builds describe "${QUALITY_BUILD_ID}" \
    --region=southamerica-east1 \
    --project="${PROJECT_ID}" \
    --format='value(status)'
)" = "SUCCESS"
```

A successful release-candidate build (`cloudbuild.candidate.yaml`, after approval) stores `build-id.txt`, `source-commit.txt`, Gitleaks, Trivy, SBOM and image identity evidence in GCS. It also publishes the candidate image through the Cloud Build `images` field with `requestedVerifyOption: VERIFIED`, so the build is not successful unless build provenance is generated.

Production promotion uses the exact candidate Build ID and the same immutable commit:

```bash
gcloud builds triggers run ai-holding-release-manual \
  --region=southamerica-east1 \
  --project="${PROJECT_ID}" \
  --sha="${RC_SHA}" \
  --substitutions="_CANDIDATE_BUILD_ID=${QUALITY_BUILD_ID},_SOURCE_COMMIT_SHA=${RC_SHA}"
```

Cloud Build then holds the release for explicit human approval. After approval, the release pipeline:

1. checks that its own source commit equals the approved commit;
2. checks the candidate Build ID/commit evidence from GCS;
3. resolves the candidate tag to an immutable Artifact Registry digest;
4. requires Cloud Build provenance for that digest;
5. signs and verifies the digest with Cosign using the release service-account OIDC identity;
6. runs the non-destructive Terraform production plan;
7. deploys the same digest without rebuilding it;
8. runs migrations, runtime identity checks, scheduler checks, PMO acceptance and Knowledge acceptance;
9. stores the release evidence under `AI-Holding/releases/<commit>/<release-build-id>/`.

The production trigger is intentionally not automatic. A repository push must never be sufficient by itself to exercise production deployment authority.
