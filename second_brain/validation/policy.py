from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from second_brain.schemas import Claim, Evaluation, LifecycleStatus, RiskLevel


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    target_status: LifecycleStatus
    reasons: tuple[str, ...]


def _independent_for_claim(claim: Claim, evaluation: Evaluation) -> bool:
    if not evaluation.independent or evaluation.target_id != claim.id:
        return False
    disallowed = {
        claim.provenance.collector_agent_id,
        claim.provenance.interpreter_agent_id,
    }
    return evaluation.evaluator_id not in {item for item in disallowed if item}


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

    relevant = [item for item in evaluations if item.target_id == claim.id]
    blocking = [item for item in relevant if item.verdict in {"REJECT", "CONFLICT"}]
    if blocking:
        reasons.append("independent review contains REJECT or CONFLICT verdict")

    approved = [
        item
        for item in relevant
        if item.verdict == "APPROVE" and _independent_for_claim(claim, item)
    ]
    distinct_approvers = {item.evaluator_id for item in approved}

    if claim.risk_level == RiskLevel.LOW:
        if independent_source_count < 2:
            reasons.append("low-risk auto-validation requires at least two independent sources")
    elif claim.risk_level == RiskLevel.MEDIUM:
        if len(distinct_approvers) < 1:
            reasons.append("medium-risk knowledge requires independent auditor approval")
    elif claim.risk_level == RiskLevel.HIGH:
        if len(distinct_approvers) < 2:
            reasons.append("high-risk knowledge requires two distinct independent approvals")
    elif claim.risk_level == RiskLevel.CRITICAL:
        if len(distinct_approvers) < 2:
            reasons.append("critical knowledge requires two distinct independent approvals")
        if not any(item.human_approval for item in approved):
            reasons.append("critical knowledge requires explicit human approval")

    if reasons:
        return ValidationResult(False, LifecycleStatus.EM_REVISAO, tuple(reasons))
    return ValidationResult(True, LifecycleStatus.CANONICO, ())
