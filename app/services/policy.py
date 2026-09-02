from dataclasses import dataclass

from app.models.entities import Agent, AgentStatus, Project, ProjectStatus, RiskLevel
from app.schemas.policy import ActionType, PolicyEvaluationRequest, PolicyOutcome


@dataclass(frozen=True)
class PolicyDecision:
    outcome: PolicyOutcome
    required_autonomy: int
    effective_autonomy: int
    reasons: tuple[str, ...]


REQUIRED_AUTONOMY: dict[ActionType, int] = {
    ActionType.internal_read: 1,
    ActionType.internal_research: 2,
    ActionType.internal_write: 3,
    ActionType.deploy_nonprod: 3,
    ActionType.deploy_production: 4,
    ActionType.external_communication: 3,
    ActionType.purchase: 1,
    ActionType.financial_transaction: 1,
    ActionType.credential_change: 1,
    ActionType.critical_delete: 1,
    ActionType.legal_commitment: 1,
}

HUMAN_GATED_ACTIONS = {
    ActionType.external_communication,
    ActionType.purchase,
    ActionType.financial_transaction,
    ActionType.credential_change,
    ActionType.critical_delete,
    ActionType.legal_commitment,
}


def evaluate_policy(
    project: Project,
    agent: Agent,
    request: PolicyEvaluationRequest,
) -> PolicyDecision:
    required = REQUIRED_AUTONOMY[request.action_type]
    effective = min(project.autonomy_level, agent.max_autonomy)
    reasons: list[str] = []

    if project.status in {ProjectStatus.paused, ProjectStatus.archived}:
        return PolicyDecision(
            PolicyOutcome.deny,
            required,
            effective,
            (f"project is {project.status.value}",),
        )

    if agent.status == AgentStatus.disabled:
        return PolicyDecision(
            PolicyOutcome.deny,
            required,
            effective,
            ("agent is disabled",),
        )

    if agent.status == AgentStatus.degraded:
        effective = min(effective, 1)
        reasons.append("degraded agent autonomy is capped at A1")

    if request.sensitive_data and request.external_party_effect:
        return PolicyDecision(
            PolicyOutcome.deny,
            required,
            effective,
            tuple(reasons + ["sensitive data cannot be exposed to an external party"]),
        )

    if request.action_type == ActionType.deploy_production and project.status != ProjectStatus.active:
        return PolicyDecision(
            PolicyOutcome.deny,
            required,
            effective,
            tuple(reasons + ["production deploy requires an active project"]),
        )

    if required > effective:
        return PolicyDecision(
            PolicyOutcome.deny,
            required,
            effective,
            tuple(reasons + [f"action requires A{required}, effective autonomy is A{effective}"]),
        )

    human_reasons: list[str] = []
    if request.action_type in HUMAN_GATED_ACTIONS:
        human_reasons.append(f"{request.action_type.value} is human-gated")
    if request.irreversible:
        human_reasons.append("action is irreversible")
    if request.financial_value is not None and request.financial_value > 0:
        human_reasons.append("action has a financial consequence")
    if request.risk_level in {RiskLevel.high, RiskLevel.critical}:
        human_reasons.append(f"risk level is {request.risk_level.value}")
    if request.external_party_effect and request.action_type != ActionType.deploy_production:
        human_reasons.append("action affects an external party")

    if human_reasons:
        return PolicyDecision(
            PolicyOutcome.require_human,
            required,
            effective,
            tuple(reasons + human_reasons),
        )

    return PolicyDecision(
        PolicyOutcome.allow,
        required,
        effective,
        tuple(reasons + ["action is within deterministic autonomy and risk limits"]),
    )
