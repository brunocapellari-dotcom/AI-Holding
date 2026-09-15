from __future__ import annotations

import hashlib
from dataclasses import dataclass

from second_brain.claims import ConflictFinding, detect_structured_conflicts
from second_brain.claims.promotion import (
    PromotionDecision,
    VerificationResult,
    canonicalize_claim,
    verify_claim,
)
from second_brain.persistence import SQLiteKnowledgeStore
from second_brain.schemas import Claim, Evaluation, Evidence, Fact, Source
from second_brain.schemas.contracts import KnowledgeRecord
from second_brain.security import scan_object_for_secrets


@dataclass(frozen=True)
class LearningRun:
    verification: VerificationResult
    promotion: PromotionDecision
    stored_fact: Fact | None
    conflicts: tuple[ConflictFinding, ...] = ()


class GovernedLearningRuntime:
    """Deterministic governance layer around agent-produced claims.

    Agents may collect and propose. This runtime is the only path in this
    reference implementation that creates a canonical Fact, and it delegates
    the decision to explicit verification/canonicalization policy.
    """

    def __init__(self, store: SQLiteKnowledgeStore) -> None:
        self.store = store

    def process_claim(
        self,
        claim: Claim,
        *,
        evidence: tuple[Evidence, ...],
        sources: tuple[Source, ...],
        evaluations: tuple[Evaluation, ...] = (),
        conflict_detected: bool = False,
    ) -> LearningRun:
        for record in (*sources, *evidence, claim, *evaluations):
            _reject_secret_material(record)

        existing_facts = tuple(
            record
            for record in self.store.all_latest(namespace_prefix=claim.namespace)
            if isinstance(record, Fact)
        )
        conflicts = detect_structured_conflicts(claim, existing_facts)
        has_conflict = conflict_detected or bool(conflicts)
        effective_evaluations = evaluations
        if conflicts and not any(item.verdict == "CONFLICT" for item in evaluations):
            conflict_evaluation = Evaluation(
                id=_stable_id("evaluation", f"structured-conflict:{claim.id}"),
                namespace=claim.namespace,
                information_class=claim.information_class,
                target_id=claim.id,
                evaluator_id="policy:structured-conflict-detector-v1",
                verdict="CONFLICT",
                independent=True,
                confidence=1.0,
                evidence_ids=list(claim.evidence_ids),
                findings=[item.message for item in conflicts],
            )
            effective_evaluations = (*evaluations, conflict_evaluation)

        for source in sources:
            self.store.put(source)
        for item in evidence:
            self.store.put(item)

        verification = verify_claim(
            claim,
            evidence,
            sources,
            conflict_detected=has_conflict,
        )
        self.store.put(verification.claim)

        promotion = canonicalize_claim(
            verification.claim,
            evidence,
            sources,
            effective_evaluations,
            conflict_detected=has_conflict,
        )
        for evaluation in promotion.evaluations:
            _reject_secret_material(evaluation)
            self.store.put(evaluation)
        if promotion.fact is not None:
            _reject_secret_material(promotion.fact)
            self.store.put(promotion.fact)
        return LearningRun(
            verification=verification,
            promotion=promotion,
            stored_fact=promotion.fact,
            conflicts=conflicts,
        )


def _reject_secret_material(record: KnowledgeRecord) -> None:
    if scan_object_for_secrets(record.model_dump(mode="json")):
        raise ValueError(f"secret-like material rejected for {record.record_type}:{record.id}")


def _stable_id(kind: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"sb:{kind}:{digest}"
