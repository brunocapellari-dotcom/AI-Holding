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
            self.store.put(evaluation)
        if promotion.fact is not None:
            self.store.put(promotion.fact)
        return LearningRun(
            verification=verification,
            promotion=promotion,
            stored_fact=promotion.fact,
        )
