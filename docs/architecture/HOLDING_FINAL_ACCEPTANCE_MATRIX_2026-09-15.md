# Holding Digital / AI Operating System — Final Acceptance Matrix

Date: 2026-09-15
Scope: complete `AI-Holding` repository
Rule: no scenario may be declared accepted from code review alone. Acceptance requires the canonical full-project gate to execute successfully.

## Status vocabulary

- `IMPLEMENTED`: production code or deterministic control exists in the PR.
- `TEST_DEFINED`: automated acceptance coverage exists in the repository.
- `PENDING_GCP_EXECUTION`: implementation and tests exist, but the canonical Cloud Build evidence has not executed successfully yet.
- `BLOCKED_GCP_AUTHORIZATION`: first-time Cloud Build GitHub App browser authorization is still required.
- `ACCEPTED`: reserved exclusively for a successful full-project run with evidence.

Current global status: `IMPLEMENTED + TEST_DEFINED + PENDING_GCP_EXECUTION + BLOCKED_GCP_AUTHORIZATION`, not `ACCEPTED`.

## Official eight E2E scenarios

| # | Scenario | Production path | Automated evidence | Current status |
|---|---|---|---|---|
| 1 | `Como está a Holding?` returns real operational state | `/api/v1/holding/executive-state`, Project Registry, Project Health, costs, revenues, risks and integrations | `tests/test_holding_operating_system.py` executive-state and registry coverage | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 2 | `Continue o AgroLog` resolves work, executes, audits and updates state | existing PMO claim/run/acceptance ledger + project/task/audit APIs | existing PMO identity, worker and production acceptance tests/jobs | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 3 | collector fails -> health degrades -> alert -> recovery | Collector Execution history + Project Health recompute + deduplicated collector-health alert | `test_collector_failure_opens_alert_and_success_recovers_it` plus collector-history test | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 4 | project declares completed without evidence -> reject | completion evidence gate on operational profile transition | `test_completed_is_rejected_without_evidence_and_accepted_after_verification` | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 5 | material spend -> approval gate | deterministic policy + explicit human gate for budget allocation | existing policy tests + budget service-account denial in Holding OS tests | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 6 | abnormal cost -> FinOps investigation | 24h spend vs preceding 7-day average and configured budget; deduplicated FinOps alert | `test_finops_anomaly_opens_investigation_and_blocks_completion` | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 7 | critical dependency fails -> graph identifies impact | typed Dependency Graph propagates blocking dependency into Project Health | dependency/health test in `test_holding_operating_system.py` | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |
| 8 | new business -> Venture Factory gates -> decision | deterministic automation, unit economics, risk, cheap-validation and evidence gates | `test_venture_factory_gate_build_hold_and_reject` | IMPLEMENTED / TEST_DEFINED / PENDING_GCP_EXECUTION |

## Full-project gate

Canonical command:

```bash
bash scripts/full_project_gate.sh
```

The gate covers the whole repository rather than a selected module:

1. Ruff lint.
2. Ruff formatting validation.
3. MyPy strict typing.
4. pip-audit dependency vulnerabilities.
5. Bandit Python security analysis.
6. Semgrep Holding-specific application security rules.
7. zizmor GitHub Actions security audit.
8. Runtime dependency license policy.
9. Alembic upgrade to head.
10. Alembic schema drift check.
11. Alembic downgrade to base.
12. Alembic re-upgrade to head.
13. second schema drift check.
14. full pytest suite with configured coverage threshold.
15. Terraform formatting.
16. Terraform init without backend.
17. Terraform validate.
18. production container build.
19. production entrypoint/import smoke test.

The canonical Cloud Build quality path additionally performs:

20. Gitleaks secret scanning.
21. Trivy Terraform/IaC HIGH/CRITICAL gate.
22. CycloneDX SBOM generation with Syft.
23. Trivy container HIGH/CRITICAL vulnerability gate.
24. publication of the exact candidate image to Artifact Registry.
25. Cloud Build verified provenance, with the build failing closed if provenance is absent.
26. durable build identity, scan and SBOM evidence in GCS.

GitHub CI is retained only as a temporary fallback until the GCP path is proven and cut over; lack of a GitHub-hosted runner is no longer the canonical execution blocker.

## Why the repository is not yet accepted

The canonical GCP quality/release path is implemented but has not yet produced live acceptance evidence. The first-time Cloud Build GitHub App connection still requires browser authorization; the bootstrap script exits fail-closed with code 20 until that authorization is complete.

GitHub Actions continues to provide a useful diagnostic signal. The latest verified behavior is:

- quality job created;
- label `ubuntu-latest` requested;
- `runner_id=0`;
- empty runner name;
- zero steps;
- no job log blob;
- job failed before repository commands executed.

Therefore the current failed GitHub check still means `runner/bootstrap failure`, not a failing or passing software test result. It must not be used as evidence either way.

After GitHub App authorization, the canonical pre-merge proof is:

```bash
bash scripts/continue_holding_gcp.sh
```

The exact-SHA quality candidate must pass before production promotion can be requested. Production promotion uses the same immutable digest, requires verified Cloud Build provenance, signs/verifies the digest with Cosign using the release service-account identity, and is held for explicit Cloud Build approval before deployment.

## Final release gate

The Holding may be declared operational only when all of the following are true in the same release candidate:

- canonical full-project gate succeeds in Cloud Build for the exact release commit;
- candidate Build ID and commit evidence match;
- Cloud Build verified provenance exists for the immutable candidate digest;
- Cosign release signature verifies against the approved production service-account identity;
- Gitleaks succeeds;
- SBOM generation succeeds;
- Trivy HIGH/CRITICAL gate succeeds;
- migrations pass forward/backward/forward checks;
- all eight official E2E scenarios pass;
- production deploy plan is non-destructive;
- database migration job succeeds;
- runtime identity checks succeed;
- PMO acceptance succeeds;
- transitional Knowledge acceptance succeeds until the external Second Brain migration is completed;
- no unresolved critical security finding exists;
- no unresolved blocker prevents the release.

A merge, deploy or status `COMPLETED` before these conditions is not permitted by the project definition of done.
