# Holding Security Test Lab — Acceptance Matrix

Date: 2026-09-15
Scope: `AI-Holding`
Principle: test actual attack surfaces; do not create fake green tests for surfaces that do not exist.

## Defense layers

- Google OIDC/WIF and service identities in production.
- deterministic authorization and human approval policy.
- private Cloud SQL networking, TLS and Secret Manager.
- no static cloud service-account keys in the deployment path.
- immutable SHA-pinned GitHub Actions.
- Gitleaks for secrets.
- Semgrep for application patterns.
- Bandit for Python security.
- pip-audit and Trivy for vulnerabilities.
- CycloneDX SBOM.
- zizmor for GitHub Actions security.
- Security Finding Registry for runtime/test findings.
- audit log for mutations.

## Threat matrix

| Threat | Current attack surface | Control / test | Acceptance rule |
|---|---|---|---|
| Prompt injection | Holding Control Plane does not execute user content as an LLM/tool prompt; shared cognition belongs to Hermes | architectural boundary; external content remains untrusted | Any future Holding LLM/tool surface must add adversarial prompt/tool tests before activation |
| Tool injection | no generic tool-execution endpoint in Holding | deterministic APIs and bounded worker execution kinds | generic remote tool invocation is prohibited in Holding |
| Secret exfiltration | source, workflow and runtime configuration | Gitleaks, Secret Manager, WIF, no static SA key path | zero detected committed secrets; no production secret exposed through API/logs |
| SQL injection | API persistence via SQLAlchemy | ORM/bound expressions; UUID and Pydantic validation; Semgrep/Bandit | no string-built SQL from request data |
| Command injection | workers/build scripts | no dynamic shell execution from request data; Semgrep blocks `os.system` and `shell=True` | zero matching production paths |
| SSRF | no current Holding endpoint dereferences arbitrary user-provided URLs | integration endpoints are metadata until explicit adapters exist | adapter activation requires outbound allowlist, timeout, redirect and private-address policy tests |
| XSS | JSON API; no Holding frontend currently | no HTML rendering surface | becomes required if a browser UI is introduced |
| CSRF | no cookie-session browser auth | production bearer/OIDC identity | becomes required if cookie-authenticated browser mutations are introduced |
| Path traversal | no arbitrary file fetch/upload API | repository paths are metadata; no filesystem dereference from API | any file adapter must validate canonical path containment before activation |
| Webhook spoofing | no inbound webhook endpoint currently | N/A for current runtime | signed payload + replay/idempotency tests mandatory before webhook activation |
| Replay attacks | service identity and task/run idempotency | OIDC expiration/audience/issuer checks; idempotency keys and run ledger | duplicate mutation/execution cannot create uncontrolled repeated effects |
| Auth bypass | production mutation endpoints | Google verified identity + canonical AgentIdentity binding + authorization tests | unauthenticated/unbound production mutation fails closed |
| Tenant escape | Holding is currently an internal single-organization control plane, not a customer multi-tenant SaaS | no false multi-tenant claim | tenant isolation suite becomes mandatory before external multi-tenancy |
| Privilege escalation | agents and service accounts | max autonomy, AgentPermission, policy engine, explicit human gates for budget/sunset | agent cannot self-grant authority or execute human-only action |
| Malicious files | no file-upload execution endpoint | N/A currently | MIME/content/malware sandbox gates required before upload activation |
| Malicious dependencies | Python, Terraform, container and Actions dependencies | pip-audit, Trivy, SBOM, license policy, SHA-pinned actions, zizmor | release blocked on prohibited license or configured severe vulnerability |
| API abuse | authenticated internal API | Cloud Run IAM/verified identity and bounded endpoints | public unauthenticated access remains forbidden; add edge rate limits if public exposure is introduced |
| Supply-chain action compromise | GitHub workflows | actions pinned to immutable SHAs; zizmor; minimal permissions | no floating third-party production action ref |

## Security finding effect on operations

Open security findings are not informational decoration:

- `CRITICAL` finding forces Project Health to at least `AT_RISK`.
- `HIGH` finding forces Project Health to at least `DEGRADED`.
- unresolved `HIGH` or `CRITICAL` finding rejects the project completion gate.
- findings preserve source, category, evidence, remediation and lifecycle state.

## Surfaces intentionally not implemented

The following are not to be created merely to make the test matrix look complete:

- a dummy webhook;
- a dummy file upload route;
- a dummy HTML frontend;
- a dummy multi-tenant layer;
- a Holding-owned generic LLM/tool executor.

Testing a fake surface would increase complexity without increasing security. When one of these capabilities becomes a real requirement, its security tests become part of the same full-project release gate before activation.

## Acceptance state

Security controls and tests in this PR remain `UNVERIFIED_BY_RUNNER` until the GitHub quality job obtains a runner and executes `scripts/full_project_gate.sh`. Code presence is not a passing test result.
