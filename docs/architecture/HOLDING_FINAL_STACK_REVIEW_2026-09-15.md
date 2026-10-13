# Holding Digital / AI Operating System — Final Stack Review

Date: 2026-09-15
Status: canonical architecture decision record for PR #53

## Non-negotiable boundary

- Holding owns operational state, governance, prioritization, PMO, risk, security, finance, audit and portfolio control.
- Hermes AI Platform owns shared AI/model/agent/skill/tool orchestration.
- Research AI owns research, discovery, comparison, testing and source acquisition.
- Segundo Cérebro owns durable knowledge.
- GitHub owns source code and technical change history.
- PostgreSQL owns Holding operational state.

No new tool may duplicate one of these responsibilities without a measured replacement case.

## KEEP / ADOPT

### PostgreSQL + Cloud SQL — KEEP

The repository already provisions PostgreSQL 16 in Google Cloud SQL with private networking, regional availability, PITR, backups, deletion protection and Secret Manager. This remains the production operational database.

Target hardening: move application database authentication from a long-lived database password to Cloud SQL automatic IAM database authentication through a supported connector after the IAM path passes the same migration, rollback, pool and E2E gates as the current path.

References:
- https://cloud.google.com/sql/docs/postgres/iam-authentication
- https://cloud.google.com/sql/docs/postgres/iam-logins
- https://cloud.google.com/sql/docs/postgres/connect-connectors

### Google Secret Manager — KEEP

Do not add Infisical/OpenBao merely because they exist. Secret Manager is already native to the chosen production cloud and avoids operating another secrets control plane. A second vault is justified only by a future multi-cloud/on-prem requirement that cannot be met cleanly by the current solution.

### OpenTelemetry Collector — ADOPT as the observability standard

Use OpenTelemetry as the vendor-neutral collection layer for traces, metrics and logs instead of adding separate per-vendor agents. Preserve Prometheus metrics compatibility.

Reference: https://github.com/open-telemetry/opentelemetry-collector

### Existing supply-chain controls — KEEP and complete

Preserve Ruff, MyPy, pytest, Alembic schema drift checks, pip-audit, Bandit, Terraform validation, container build verification, CycloneDX SBOM and Trivy. Complete the intended gate with secret scanning, SAST and license policy enforcement rather than introducing overlapping scanners.

## BENCHMARK BEFORE REPLACEMENT

### Temporal — BENCHMARK

Temporal is a strong durable-execution candidate because it provides resilient workflows and retry semantics. It must not be installed beside the current worker/scheduler/runtime stack as another central orchestrator. Benchmark it against the existing execution ledger, workers, Cloud Scheduler and AgentOS direction. Adopt only through a replacement ADR with migration and rollback.

Reference: https://github.com/temporalio/temporal

### OpenFGA — BENCHMARK

OpenFGA is appropriate for fine-grained ReBAC/ABAC authorization. The Holding already has deterministic policy and identity controls; therefore OpenFGA must prove a concrete gap before adoption. It may replace/extend authorization later, but it must not become a second overlapping authorization truth.

Reference: https://github.com/openfga/openfga

## RESERVE

### AlloyDB — RESERVE

Do not migrate because it is newer or faster on benchmarks. Cloud SQL is the lower-complexity managed PostgreSQL target. Consider AlloyDB only when measured throughput, latency, analytical workload, replica or availability requirements exceed the Cloud SQL design and the economic case is positive.

Reference: https://cloud.google.com/products/alloydb

## REJECT FOR THE CURRENT ARCHITECTURE

- A graph database solely for the dependency graph: store typed dependency edges in PostgreSQL first and use recursive queries/materialized views as needed.
- A second central agent runtime while AgentOS/current execution stack remains active.
- A second model router: Hermes owns model routing.
- A second knowledge database in Holding: Segundo Cérebro owns durable knowledge.
- A second secrets manager while Google Secret Manager satisfies production requirements.
- Parallel Replit or Claude Code state: development clients must work through Git branches/PRs; GitHub remains canonical.

## Replit and Claude Code operating policy

Replit and Claude Code are approved future development clients, not independent environments of truth.

Rules:
1. No independent production database.
2. No direct production secrets.
3. No direct production deployment authority.
4. Work occurs on Git branches and enters through PR review/gates.
5. Generated code is subject to the same tests, SAST, dependency, secret, SBOM, container and E2E gates.
6. No automatic main-branch merge for high-risk or governance-sensitive changes.
7. They are not activated for Holding development until the current repository branch is internally coherent and its full-project gate can execute.

## Tool-sprawl decisions

| Capability | Decision | Reason |
|---|---|---|
| FastAPI | KEEP | Existing control-plane API; no replacement benefit identified |
| SQLAlchemy/Alembic | KEEP | Existing persistence/migration contract |
| PostgreSQL/Cloud SQL | KEEP | Canonical operational DB and already provisioned |
| Google Secret Manager | KEEP | Native, already integrated, avoids another vault |
| OpenTelemetry | ADOPT | Unifies telemetry without vendor lock-in |
| Temporal | BENCHMARK | Potential durable-workflow replacement, not additive runtime |
| OpenFGA | BENCHMARK | Potential fine-grained authorization extension/replacement |
| AlloyDB | RESERVE | Upgrade only from measured need |
| Separate graph DB | REJECT | PostgreSQL is sufficient for initial dependency graph |
| Duplicate model router | REJECT | Hermes responsibility |
| Duplicate knowledge store | REJECT | Segundo Cérebro responsibility |
| Replit as source of truth | REJECT | GitHub remains canonical |
| Claude Code as source of truth | REJECT | GitHub remains canonical |

## Promotion gate

No BENCHMARK or RESERVE item becomes ADOPT without:
- documented gap;
- alternative comparison;
- license/security review;
- operational cost;
- migration and rollback plan;
- no-duplication check;
- full-project tests;
- independent audit evidence.
