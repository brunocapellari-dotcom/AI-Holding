from __future__ import annotations

from dataclasses import dataclass

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

        for source in sources:
            self.store.put(source)
        for item in evidence:
            self.store.put(item)

        verification = verify_claim(
            claim,
            evidence,
            sources,
            conflict_detected=conflict_detected,
        )
        self.store.put(verification.claim)

        promotion = canonicalize_claim(
            verification.claim,
            evidence,
            sources,
            evaluations,
            conflict_detected=conflict_detected,
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
        )


def _reject_secret_material(record: KnowledgeRecord) -> None:
    if scan_object_for_secrets(record.model_dump(mode="json")):
        raise ValueError(f"secret-like material rejected for {record.record_type}:{record.id}")
