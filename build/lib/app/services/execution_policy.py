from __future__ import annotations

from dataclasses import dataclass

from app.models.entities import RiskLevel
from app.schemas.api import ExecutionKind
from app.schemas.policy import ActionType


@dataclass(frozen=True)
class ExecutionPolicyProfile:
    action_type: ActionType
    risk_level: RiskLevel
    irreversible: bool = False
    external_party_effect: bool = False
    sensitive_data: bool = False


EXECUTION_POLICY_PROFILES: dict[ExecutionKind, ExecutionPolicyProfile] = {
    ExecutionKind.control_plane_health: ExecutionPolicyProfile(
        action_type=ActionType.internal_read,
        risk_level=RiskLevel.low,
    ),
    ExecutionKind.knowledge_gap_scan: ExecutionPolicyProfile(
        action_type=ActionType.internal_read,
        risk_level=RiskLevel.low,
    ),
    ExecutionKind.knowledge_outcome_review: ExecutionPolicyProfile(
        action_type=ActionType.internal_read,
        risk_level=RiskLevel.low,
    ),
}


def execution_policy_profile(execution_kind: str | None) -> ExecutionPolicyProfile | None:
    if execution_kind is None:
        return None
    try:
        kind = ExecutionKind(execution_kind)
    except ValueError:
        return None
    return EXECUTION_POLICY_PROFILES.get(kind)
