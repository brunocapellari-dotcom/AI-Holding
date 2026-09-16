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

## Migration acceptance

A project is considered migrated only when:

- its deterministic whole-project gate passes in Cloud Build;
- its live/scheduled workloads run from Cloud Run Jobs/Scheduler where applicable;
- logs and evidence are durable in GCP;
- required secrets come from Secret Manager;
- the project can run with GitHub Actions hosted minutes set effectively to zero;
- rollback/re-run is documented and tested;
- no duplicate scheduler remains active.
