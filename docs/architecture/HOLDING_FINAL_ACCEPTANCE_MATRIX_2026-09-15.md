# Holding Digital / AI Operating System — Final Acceptance Matrix

Date: 2026-09-15
Scope: complete `AI-Holding` repository
Rule: no scenario may be declared accepted from code review alone. Acceptance requires the canonical full-project gate to execute successfully.

## Status vocabulary

- `IMPLEMENTED`: production code or deterministic control exists in the PR.
- `TEST_DEFINED`: automated acceptance coverage exists in the repository.
- `BLOCKED_RUNNER`: GitHub created the quality job but assigned no runner and executed zero steps.
- `ACCEPTED`: reserved exclusively for a successful full-project run with evidence.

Current global status: `IMPLEMENTED + TEST_DEFINED + BLOCKED_RUNNER`, not `ACCEPTED`.

## Official eight E2E scenarios

| # | Scenario | Production path | Automated evidence | Current status |
|---|---|---|---|---|
| 1 | `Como está a Holding?` returns real operational state | `/api/v1/holding/executive-state`, Project Registry, Project Health, costs, revenues, risks and integrations | `tests/test_holding_operating_system.py` executive-state and registry coverage | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 2 | `Continue o AgroLog` resolves work, executes, audits and updates state | existing PMO claim/run/acceptance ledger + project/task/audit APIs | existing PMO identity, worker and production acceptance tests/jobs | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 3 | collector fails -> health degrades -> alert -> recovery | Collector Execution history + Project Health recompute + deduplicated collector-health alert | `test_collector_failure_opens_alert_and_success_recovers_it` plus collector-history test | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 4 | project declares completed without evidence -> reject | completion evidence gate on operational profile transition | `test_completed_is_rejected_without_evidence_and_accepted_after_verification` | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 5 | material spend -> approval gate | deterministic policy + explicit human gate for budget allocation | existing policy tests + budget service-account denial in Holding OS tests | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 6 | abnormal cost -> FinOps investigation | 24h spend vs preceding 7-day average and configured budget; deduplicated FinOps alert | `test_finops_anomaly_opens_investigation_and_blocks_completion` | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 7 | critical dependency fails -> graph identifies impact | typed Dependency Graph propagates blocking dependency into Project Health | dependency/health test in `test_holding_operating_system.py` | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |
| 8 | new business -> Venture Factory gates -> decision | deterministic automation, unit economics, risk, cheap-validation and evidence gates | `test_venture_factory_gate_build_hold_and_reject` | IMPLEMENTED / TEST_DEFINED / BLOCKED_RUNNER |

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

GitHub CI additionally performs Gitleaks secret scanning, CycloneDX SBOM generation and Trivy container vulnerability scanning.

## Why the repository is not yet accepted

The latest verified GitHub Actions behavior before this matrix was created was:

- quality job created;
- label `ubuntu-latest` requested;
- `runner_id=0`;
- empty runner name;
- zero steps;
- no job log blob;
- job failed before repository commands executed.

Therefore a failed GitHub check currently means `runner/bootstrap failure`, not a failing or passing software test result. It must not be used as evidence either way.

## Final release gate

The Holding may be declared operational only when all of the following are true in the same release candidate:

- canonical full-project gate succeeds;
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
