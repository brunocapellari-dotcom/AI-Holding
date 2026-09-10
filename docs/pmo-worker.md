# PMO worker lifecycle

The first production PMO worker is deliberately bounded. It is not a generic code or shell executor.

## Execution contract

A task is eligible only when all of the following are true:

- project is active;
- task is `ready`;
- dependencies are complete;
- there is no active run for the task;
- task is unassigned or already assigned to the claiming agent;
- `execution_kind` is explicitly supported by the worker.

The initial supported kind is `control_plane_health`. Tasks without an execution kind are never claimed by this worker.

## Lifecycle

1. Fetch a Google identity token for the Control Plane audience.
2. Claim one compatible task through `/api/v1/pmo/claim`; production derives the canonical agent from the verified service-account binding rather than trusting a client-supplied agent identifier.
3. Move the generated run from `queued` to `running`.
4. Execute the deterministic handler for the declared execution kind.
5. Store structured evidence in the successful run.
6. Move the task to `review`; the worker never marks its own task `done`.
7. On execution failure, mark the run `failed`, block the task with the failure stage, create a `sev3` incident when possible, and fail the Cloud Run Job execution.

Worker failures have deterministic stage exit codes so production diagnosis does not require broad log-reader permission for the deployment identity.

## Production identity

The Cloud Run Job uses `holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com`. It has Cloud Run invoker access to the Control Plane and is bound to the canonical `PMO_IA` identity. The Control Plane applies a second authorization layer after Google identity verification.

## Acceptance gate

Provisioning the worker does not by itself authorize unattended operation. Every production release executes a bounded acceptance flow that creates one idempotent health task, runs the authenticated worker, verifies structured `/healthz` and `/readyz` evidence, and disables `PMO_IA` if acceptance fails.

## Scheduler safety

Scheduling is infrastructure-gated separately from worker deployment:

- `enable_pmo_scheduler` defaults to `false`, so no Cloud Scheduler resource or scheduler identity exists by default;
- even when explicitly provisioned, `pmo_scheduler_paused` defaults to `true`;
- the scheduler uses a dedicated service account with only `roles/run.invoker` on the PMO Cloud Run Job;
- it calls the Google Cloud Run Jobs API with an OAuth token and no static credential;
- scheduler-level automatic retries are disabled; task/run idempotency and failure handling remain inside the Control Plane;
- the initial scheduled worker remains limited to `control_plane_health` and one task per job execution.

Unpausing recurring execution is a separate operational decision after production acceptance has succeeded and the cadence/cost has been reviewed.
