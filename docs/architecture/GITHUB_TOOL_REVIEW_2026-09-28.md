# GitHub Tool Review — 2026-09-28

Status: canonical incremental review for Holding PR #53.

## Scope

This review re-checked active upstream projects against the current Holding boundary. The goal is not to maximize tool count; it is to add capabilities that close a measured gap and reject parallel control planes.

## Decisions

### ADOPT — Cloud Build verified provenance

Use Artifact Registry images emitted through the Cloud Build `images` field with `requestedVerifyOption: VERIFIED`.

Reason: provenance is generated and verified by the already selected execution platform. This supersedes any plan to introduce a GitHub-Actions-specific provenance generator.

Implementation: `cloudbuild.yaml` now publishes an immutable candidate image tagged by Build ID after all quality/security gates and requires verified provenance before the build can succeed.

### ADOPT — Cosign for release identity

Use Sigstore Cosign only at release promotion, signing the immutable digest with a short-lived OIDC identity token from the user-specified Cloud Build service account. Never create a static signing key merely for CI.

Pinned reviewed upstream release: `sigstore/cosign v3.1.3`.

Cosign complements Cloud Build provenance: provenance proves how the artifact was built; the Cosign signature records the trusted release identity.

### ADOPT — OpenSSF Scorecard for external intake

Keep OpenSSF Scorecard in the open-source intake path. It is an upstream repository posture heuristic, not a replacement for Trivy, Semgrep, Gitleaks, license analysis or human review.

Reviewed upstream release: `ossf/scorecard v5.5.0`.

### BENCHMARK — ToolHive, but not as Holding runtime

ToolHive remains useful as a reference/benchmark for MCP registry, isolation, identity, policy, audit and provenance. Its cloud operating model is currently Kubernetes-oriented, while the Holding canonical runtime is Cloud Run/Cloud Build.

Do not introduce Kubernetes only to run ToolHive. Reuse its security concepts in Hermes / the future MCP gateway and reassess if the ecosystem later has a justified Kubernetes control plane.

Reviewed upstream release: `stacklok/toolhive v0.51.4`.

### BENCHMARK — Temporal only as a replacement candidate

Temporal remains the only durable-workflow replacement benchmark because it could replace retry/durable-execution responsibilities if the current PMO ledger proves insufficient.

Reviewed Python SDK release: `temporalio/sdk-python 1.33.0`.

### REJECT in Holding core — Prefect and Dagster

Both are active, mature projects, but adding either beside PMO + Cloud Scheduler + the operational ledger creates another orchestration truth. Their strengths do not close a current Holding gap.

Reviewed releases:
- Prefect `3.8.7`;
- Dagster `1.13.24`.

### KEEP OUT OF HOLDING CORE — Phoenix and Promptfoo

Phoenix and Promptfoo remain corporate AI-observability/evaluation tools, but their execution belongs to Hermes/Research AI and AI-enabled project gates. The Holding consumes their audited outputs; it does not become another LLM evaluation platform.

### NO ADDITIVE AUTHORIZATION ENGINE

OPA, Cerbos and OpenFGA are all viable policy/authorization projects. The Holding already has deterministic identity, RBAC and policy enforcement. OpenFGA remains the existing replacement benchmark; no second authorization truth is introduced without a concrete missing policy case.

### REJECT — SLSA GitHub Generator

Do not add it to the Holding. It is GitHub-Actions-centric and would reverse the decision to move execution to Google Cloud. Cloud Build verified provenance is the native replacement.

## Resulting supply-chain path

`source -> Gitleaks -> full project gate -> Trivy IaC -> SBOM/Syft -> Trivy image -> immutable Artifact Registry candidate -> Cloud Build verified provenance -> release identity/Cosign -> Terraform non-destructive plan -> controlled deploy -> acceptance -> audit evidence`

## No-duplication summary

- Cloud Build owns build execution and provenance.
- Cosign adds release identity only.
- Trivy keeps vulnerability + IaC scanning.
- Syft keeps SBOM.
- Gitleaks keeps secret scanning.
- Semgrep/Bandit keep source security analysis.
- Renovate keeps dependency maintenance.
- Temporal stays benchmark-only.
- ToolHive stays benchmark/reference-only.
- Prefect/Dagster are not added.
- OPA/Cerbos/OpenFGA are not added as parallel policy engines.
