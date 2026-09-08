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

1. Resolve canonical `PMO_IA` identity from the Control Plane.
2. Claim one compatible task through `/api/v1/pmo/claim`.
3. Move the generated run from `queued` to `running`.
4. Execute the deterministic handler for the declared execution kind.
5. Store structured evidence in the successful run.
6. Move the task to `review`; the worker never marks its own task `done`.
7. On execution failure, mark the run `failed`, block the task with the error, create a `sev3` incident, and fail the Cloud Run Job execution.

## Production identity

The Cloud Run Job uses `holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com`. It has Cloud Run invoker access to the Control Plane and is bound to the canonical `PMO_IA` identity. The Control Plane applies a second authorization layer after Google identity verification.

## Activation gate

Provisioning the worker does not activate `PMO_IA` and does not schedule the job. Activation and scheduling occur only after the worker image, migration, authorization boundary, and a controlled end-to-end smoke execution have been validated in production.
