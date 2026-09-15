from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from second_brain.schemas import (
    Claim,
    EpistemicNature,
    Evaluation,
    Evidence,
    Fact,
    LifecycleStatus,
    Provenance,
    Source,
)
from second_brain.validation import ValidationResult, evaluate_claim_for_canonicalization


@dataclass(frozen=True)
class VerificationResult:
    claim: Claim
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PromotionDecision:
    validation: ValidationResult
    fact: Fact | None
    evaluations: tuple[Evaluation, ...]


def verify_claim(
    claim: Claim,
    evidence: Iterable[Evidence],
    sources: Iterable[Source],
    *,
    conflict_detected: bool = False,
    minimum_confidence: float = 0.60,
) -> VerificationResult:
    evidence_by_id = {item.id: item for item in evidence}
    source_by_id = {item.id: item for item in sources}
    reasons: list[str] = []

    missing = [evidence_id for evidence_id in claim.evidence_ids if evidence_id not in evidence_by_id]
    if missing:
        reasons.append(f"missing evidence: {', '.join(sorted(missing))}")

    source_ids: set[str] = set()
    for evidence_id in claim.evidence_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            continue
        source_ids.add(item.source_id)
        source = source_by_id.get(item.source_id)
        if source is None:
            reasons.append(f"missing source for evidence: {item.id}")
        elif not source.approved_for_ingestion:
            reasons.append(f"source is not approved for ingestion: {source.id}")

    if conflict_detected:
        status = LifecycleStatus.CONFLITANTE
        reasons.append("unresolved conflict detected")
    elif claim.confidence < minimum_confidence:
        status = LifecycleStatus.BAIXA_CONFIANCA
        reasons.append("claim confidence below verification threshold")
    elif reasons:
        status = LifecycleStatus.EM_REVISAO
    elif not source_ids:
        status = LifecycleStatus.EM_REVISAO
        reasons.append("claim has no independently traceable source")
    else:
        status = LifecycleStatus.VALIDADO

    verified = claim.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
    return VerificationResult(claim=verified, reasons=tuple(reasons))


def canonicalize_claim(
    claim: Claim,
    evidence: Iterable[Evidence],
    sources: Iterable[Source],
    evaluations: Iterable[Evaluation],
    *,
    conflict_detected: bool = False,
) -> PromotionDecision:
    evidence_items = tuple(evidence)
    source_by_id = {item.id: item for item in sources}
    evidence_by_id = {item.id: item for item in evidence_items}
    evaluations_tuple = tuple(evaluations)

    missing_evidence = [item_id for item_id in claim.evidence_ids if item_id not in evidence_by_id]
    if missing_evidence:
        result = ValidationResult(
            approved=False,
            target_status=LifecycleStatus.EM_REVISAO,
            reasons=(f"missing evidence: {', '.join(sorted(missing_evidence))}",),
        )
        return PromotionDecision(result, None, evaluations_tuple)

    source_ids = {evidence_by_id[item_id].source_id for item_id in claim.evidence_ids}
    unapproved_sources = sorted(
        source_id
        for source_id in source_ids
        if source_id not in source_by_id or not source_by_id[source_id].approved_for_canonicalization
    )
    if unapproved_sources:
        result = ValidationResult(
            approved=False,
            target_status=LifecycleStatus.EM_REVISAO,
            reasons=(
                f"source not approved for canonicalization: {', '.join(unapproved_sources)}",
            ),
        )
        return PromotionDecision(result, None, evaluations_tuple)

    result = evaluate_claim_for_canonicalization(
        claim,
        evaluations_tuple,
        independent_source_count=len(source_ids),
        conflict_detected=conflict_detected,
    )
    if not result.approved:
        return PromotionDecision(result, None, evaluations_tuple)

    effective_evaluations = evaluations_tuple
    if not effective_evaluations:
        automatic = Evaluation(
            id=_stable_id("evaluation", f"auto:{claim.id}:policy-v1"),
            namespace=claim.namespace,
            information_class=claim.information_class,
            target_id=claim.id,
            evaluator_id="policy:auto-low-risk-v1",
            verdict="APPROVE",
            independent=True,
            confidence=claim.confidence,
            evidence_ids=list(claim.evidence_ids),
            findings=["automatic low-risk validation policy satisfied"],
            human_approval=False,
        )
        effective_evaluations = (automatic,)

    approved_ids = [
        item.id
        for item in effective_evaluations
        if item.verdict == "APPROVE" and item.independent
    ]
    fact = Fact(
        id=_stable_id("fact", f"{claim.id}:{claim.statement}"),
        namespace=claim.namespace,
        information_class=claim.information_class,
        statement=claim.statement,
        status=LifecycleStatus.CANONICO,
        nature=claim.nature if isinstance(claim.nature, EpistemicNature) else EpistemicNature.STRUCTURAL,
        confidence=claim.confidence,
        risk_level=claim.risk_level,
        claim_ids=[claim.id],
        evidence_ids=list(claim.evidence_ids),
        validation_ids=approved_ids,
        provenance=Provenance(
            source_id=claim.provenance.source_id,
            source_uri=claim.provenance.source_uri,
            author_or_institution=claim.provenance.author_or_institution,
            document_id=claim.provenance.document_id,
            collector_agent_id=claim.provenance.collector_agent_id,
            interpreter_agent_id=claim.provenance.interpreter_agent_id,
            method_id=claim.provenance.method_id,
            evidence_ids=list(claim.evidence_ids),
            confidence=claim.confidence,
            notes=claim.provenance.notes,
        ),
        temporal=claim.temporal,
        supersedes_id=claim.supersedes_id,
    )
    return PromotionDecision(result, fact, effective_evaluations)


def _stable_id(kind: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"sb:{kind}:{digest}"
