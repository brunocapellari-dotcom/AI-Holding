# Continuous Evolution Policy

## Default operating mode

The ecosystem evolves continuously. Stopping because a chat ended, a PR was opened, or one task completed is not an acceptable terminal state.

The Holding must always select the next highest-value unblocked task until every project reaches its objective acceptance gates.

## Autonomous actions

The system may proceed without human approval for:

- reading repositories, logs, CI results and documentation;
- creating branches, commits, tests, documentation and pull requests;
- fixing lint, typing, tests, security findings and non-breaking dependency issues;
- implementing reversible application code and internal contracts;
- adding observability, validation, test coverage and recovery tooling;
- closing obsolete/duplicate engineering work when evidence is clear;
- merging low-risk changes only after mandatory CI/security/E2E gates pass and repository policy permits it;
- continuing to the next backlog item after a successful merge.

## Human approval remains mandatory

Explicit approval is required for:

- production data deletion or irreversible migration;
- expenditure, subscriptions, paid infrastructure commitments or capital allocation;
- credentials, secrets or identity changes that expand privilege;
- legal/contractual commitments;
- public publication with material reputational risk;
- destructive production infrastructure changes;
- real-money trading or financial execution;
- any action classified high/critical whose effect cannot be safely rolled back.

Autonomy is not authority.

## Work selection

Priority is determined in this order:

1. blockers preventing CI, deploy, data freshness or E2E operation;
2. shared platform dependencies affecting multiple projects;
3. broken security, backup, restore or observability gates;
4. incomplete end-to-end paths for the highest-priority production project;
5. remaining product functionality;
6. optimizations and research-driven improvements.

Do not expand scope while a higher-priority operational blocker is unresolved.

## Definition of done

A project is not complete because code exists. Completion requires the project-specific acceptance criteria plus:
CI, security, E2E, observability, recovery, documentation and operational evidence where applicable.

When one task reaches its gate, immediately select the next unblocked task.
