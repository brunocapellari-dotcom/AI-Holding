# Holding Execution Fabric Supervisor

Status: canonical design for the shared Google Cloud execution fabric.

## Scope

The Holding supervises the repositories executed inside the shared GCP project
`ai-holding-prod-bc`.

The shared scope is:

- AI-Holding
- Geopolitical-Watch
- Mercado-Financeiro
- Sports-Intelligence
- Game-Studio
- Second-Brain
- Hermes-AI-Platform
- Personal-Performance-Health-OS
- Research-AI
- Content-Factory
- WHATSAPP_AI

AgroLogMT is intentionally excluded because it operates in its own dedicated
Google Cloud project.

## Data path

```text
GitHub private repository
        |
        v
Cloud Build trigger
        |
        +--> quality/security/E2E gate
        |
        +--> GCS evidence
        |
        v
Cloud Build API (read only)
        |
        v
holding-control-plane-cloud-build-collector
        |
        v
CollectorRegistration / CollectorExecution
        |
        +--> Project Health
        +--> Holding Alerts
        +--> /holding/execution-fabric
        +--> Executive State
        |
        v
CEO IA / PMO / Hermes
```

No second execution database is introduced. Cloud Build evidence is projected
into the existing Holding collector/evidence model.

## Least privilege

The collector uses the PMO runtime identity and receives only
`roles/cloudbuild.builds.viewer`.

It does not receive:

- build editor;
- build creator;
- trigger editor;
- Cloud Run admin;
- project editor;
- project owner.

The Cloud Scheduler identity can only invoke the bounded collector Cloud Run
Job.

## Build-state semantics

- `SUCCESS`: quality evidence is healthy.
- `QUEUED`, `PENDING`, `WORKING`: observed successfully and does not
  degrade project health.
- terminal build failure: collector becomes failing immediately and opens an
  action-required health signal.
- missing evidence: degraded until a build is observed.

Generic external-data collectors keep the existing multi-failure threshold.
A Cloud Build quality failure is deterministic evidence and therefore needs no
three-strike delay.

## Failure diagnosis

The collector stores only sanitized build metadata:

- build id;
- status;
- branch;
- commit SHA;
- trigger id;
- log URL;
- failure type;
- step id/name;
- step status;
- exit code.

Raw log output and Cloud Build `failureInfo.detail` are not copied into the
Holding database because they may contain sensitive material.

The Execution Fabric classifies failures into bounded categories such as:

- security-secret;
- security-supply-chain;
- infrastructure;
- ci-toolchain;
- project-quality;
- dependency-quality;
- transient-platform;
- unknown.

The result includes a remediation owner and recommended next action.

## Authority boundary

Observation and diagnosis do not grant execution authority.

The supervisor does not automatically:

- rerun a failed build;
- weaken or bypass a quality gate;
- merge a pull request;
- deploy production;
- change IAM;
- spend material capital;
- alter a project security policy.

Only a narrowly identified transient platform failure may be marked
`retry_safe=true`. Even then, automatic rerun requires a separately reviewed
policy and permission before it can be enabled.

## Executive contract

`GET /api/v1/holding/execution-fabric` exposes the current shared execution
portfolio with counts for:

- success;
- working;
- queued;
- failure;
- unknown.

The same payload is embedded in the Holding Executive State so CEO IA, PMO and
Hermes consume one canonical operational view.

## Production acceptance

The Holding release gate must verify that:

1. Cloud Build API is enabled.
2. PMO has only read access to build state.
3. the collector Cloud Run Job exists.
4. Cloud Scheduler has only invoke permission.
5. the collector scheduler is enabled.
6. AgroLogMT is not inside the shared repository allowlist.
7. production deployment remains non-destructive.
8. PMO and Knowledge acceptance still pass.

The Holding must never report a project as completed merely because a build is
green. Build evidence is one input to the broader completion gate.
