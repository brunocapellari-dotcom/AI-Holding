from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from second_brain.schemas import Claim, Evaluation, LifecycleStatus, RiskLevel


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    target_status: LifecycleStatus
    reasons: tuple[str, ...]


def evaluate_claim_for_canonicalization(
    claim: Claim,
    evaluations: Iterable[Evaluation],
    *,
    independent_source_count: int,
    conflict_detected: bool = False,
) -> ValidationResult:
    reasons: list[str] = []
    if claim.status != LifecycleStatus.VALIDADO:
        reasons.append("claim must be VALIDADO before canonicalization")
    if not claim.evidence_ids:
        reasons.append("claim has no evidence")
    if conflict_detected:
        reasons.append("unresolved contradiction exists")
    if claim.confidence < 0.80:
        reasons.append("confidence below canonical threshold")

    approved = [item for item in evaluations if item.verdict == "APPROVE" and item.independent]
    if claim.risk_level == RiskLevel.LOW and independent_source_count < 2:
        reasons.append("low-risk auto-validation requires at least two independent sources")
    elif claim.risk_level == RiskLevel.MEDIUM and not approved:
        reasons.append("medium-risk knowledge requires independent auditor approval")
    elif claim.risk_level == RiskLevel.HIGH and len(approved) < 2:
        reasons.append("high-risk knowledge requires two independent approvals")
    elif claim.risk_level == RiskLevel.CRITICAL:
        if len(approved) < 2:
            reasons.append("critical knowledge requires two independent approvals")
        if not any(item.human_approval for item in approved):
            reasons.append("critical knowledge requires explicit human approval")

    if reasons:
        return ValidationResult(False, LifecycleStatus.EM_REVISAO, tuple(reasons))
    return ValidationResult(True, LifecycleStatus.CANONICO, ())
