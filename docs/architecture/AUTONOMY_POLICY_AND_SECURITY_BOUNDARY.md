# Autonomy Policy and Security Boundary

Status: production architecture
Date: 2026-09-02

## Purpose

The Holding must be autonomous for reversible, low-risk internal work without allowing an LLM, prompt, worker, or tool call to redefine its own authority. Autonomy is therefore enforced by deterministic application and infrastructure controls, not by model instructions alone.

## Decision hierarchy

Effective autonomy is the minimum of the project's configured autonomy and the agent's maximum autonomy. Degraded agents are capped at A1. Disabled agents and paused or archived projects fail closed.

Current deterministic minimums:

| Action | Minimum autonomy | Additional gate |
| --- | ---: | --- |
| Internal read | A1 | none |
| Internal research | A2 | none |
| Internal write | A3 | risk rules apply |
| Non-production deploy | A3 | risk rules apply |
| Production deploy | A4 | active project required |
| External communication | A3 | human approval |
| Purchase | A1 | human approval |
| Financial transaction | A1 | human approval |
| Credential change | A1 | human approval |
| Critical delete | A1 | human approval |
| Legal commitment | A1 | human approval |

The low nominal autonomy level on inherently sensitive actions does not grant execution rights: those actions are always human-gated.

## Mandatory human gates

Human approval is required when any of the following is true:

- the action belongs to a permanently human-gated category;
- the action is irreversible;
- it has a financial consequence;
- risk is high or critical;
- it affects an external party, except the separately controlled production-deploy path.

Sensitive data combined with an external-party effect is denied rather than merely escalated.

## Approval binding and replay safety

A human approval is bound to the exact normalized policy request. The Control Plane computes a SHA-256 fingerprint over the complete request payload and records it with the decision. Reusing the same action key with changed context is rejected. This prevents a valid approval for one operation from being replayed for another operation.

## Prompt-injection boundary

Free-text summaries and future LLM outputs are untrusted data. They may describe an intended action, but they do not select the policy result, modify autonomy, grant credentials, or bypass a gate. The deterministic fields supplied to the Policy Engine and the canonical Project/Agent records are the authority inputs.

Model instructions must never be treated as authorization. Tool executors must evaluate policy before privileged side effects and must refuse execution when the result is `deny` or `require_human` without a matching approved decision.

## Identity boundary

`X-Actor` currently exists for application audit attribution and must not be considered authentication. Production Cloud Run remains IAM-private. Before autonomous agents receive invoke permission or human approvals are exposed through an interface, caller identity must be derived from authenticated Google identity/service identity rather than a caller-controlled header.

No agent should receive broad cloud credentials. Service accounts must be capability-specific and use least privilege. Static long-lived Google Cloud keys are prohibited; GitHub deployment uses Workload Identity Federation.

## Data and database controls

- Database credentials live in Secret Manager, not source control.
- Cloud SQL uses private networking.
- Production data is protected by backups, point-in-time recovery, and deletion protection.
- A partial unique database index guarantees at most one queued/running execution per task, protecting against concurrent scheduler races beyond application-level checks.
- Alembic schema drift is a CI failure; ORM changes must be accompanied by explicit migrations.

## Audit requirements

Every policy evaluation is written to the audit log with action key, action type, agent, outcome, required autonomy, and effective autonomy. Human-gate creation and final decision resolution are separately auditable events.

## Failure policy

Security-sensitive ambiguity fails closed. Missing project/agent identity, disabled agents, insufficient autonomy, sensitive external disclosure, approval-key mismatch, and invalid state transitions must not degrade into best-effort execution.

## Reuse guidance

Other Holding projects should reuse the same pattern:

1. canonical state outside the LLM;
2. deterministic policy before side effects;
3. exact-request approval binding;
4. idempotency and database-enforced concurrency constraints;
5. least-privilege identity at the infrastructure boundary;
6. append-only audit evidence sufficient to reconstruct why an action was allowed, denied, or escalated.
