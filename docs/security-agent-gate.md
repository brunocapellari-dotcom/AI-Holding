# Service-agent authorization boundary

Production mutations are fail-closed for authenticated service accounts.

- Cloud Run IAM remains the outer invocation boundary.
- `AgentIdentity` binds a verified Google issuer/subject to one canonical agent.
- A canonical agent must be active before it can perform an agent mutation.
- Service-account permissions are code-owned and explicit in `app/core/authorization.py`.
- PMO may claim work, transition only its assigned running task to review/blocked, transition only its own run, evaluate policy only for itself, and create incidents.
- PMO cannot create projects, agents, arbitrary tasks/runs, resolve human decisions, verify acceptance criteria, or transition/resolve incidents.
- Human operators may use governance mutations only after passing the authenticated Cloud Run boundary; the PMO claim endpoint is service-agent only.
- Local development and tests preserve local ergonomics, while production enforcement is covered by route-boundary tests.

This gate intentionally keeps `PMO_IA` disabled until the production worker/executor lifecycle is implemented and validated end to end.
