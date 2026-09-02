# Canonical Holding bootstrap

Date: 2026-09-02

The bootstrap registers the Holding portfolio and governance-agent definitions in the Control Plane without claiming runtime execution that has not been provisioned.

Rules:

- Re-running the bootstrap is idempotent.
- Existing operational state such as project priority or agent status is not overwritten.
- Structural identity drift in project names, repositories or hierarchy fails closed.
- Pecuária and Maritime Intelligence are children of AgroLog MT and share its canonical repository.
- Governance agents are created disabled with `model_policy={"status":"unconfigured"}` until a verified runtime identity and model route exist.
- Repository fields are set only for repositories verified as present in the connected GitHub account: `brunocapellari-dotcom/AI-Holding`, `brunocapellari-dotcom/AgroLogMT` and `brunocapellari-dotcom/Geopolitical-Watch`.

This bootstrap is portfolio registration only. It does not create fake tasks, runs, incidents, progress or agent activity.

## Operational note

The bootstrap code is intentionally independent from model providers. Activating an agent requires a separately provisioned runtime identity, an explicit model route and a policy-compatible autonomy level. This prevents a database row from being mistaken for a live autonomous worker.
