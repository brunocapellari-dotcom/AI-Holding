from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from second_brain.claims import (
    ConflictFinding,
    SupersessionCandidate,
    detect_structured_conflicts,
    find_supersession_candidates,
)
from second_brain.claims.promotion import (
    PromotionDecision,
    VerificationResult,
    canonicalize_claim,
    verify_claim,
)
from second_brain.persistence import SQLiteKnowledgeStore
from second_brain.schemas import Claim, Evaluation, Evidence, Fact, LifecycleStatus, Source
from second_brain.schemas.contracts import KnowledgeRecord
from second_brain.security import scan_object_for_secrets


@dataclass(frozen=True)
class LearningRun:
    verification: VerificationResult
    promotion: PromotionDecision
    stored_fact: Fact | None
    conflicts: tuple[ConflictFinding, ...] = ()
    superseded_fact_ids: tuple[str, ...] = ()


class GovernedLearningRuntime:
    """Deterministic governance layer around agent-produced claims."""

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
        supersession_candidates = find_supersession_candidates(claim, existing_facts)
        conflicts = detect_structured_conflicts(claim, existing_facts)
        ambiguous_supersession = len(supersession_candidates) > 1
        has_conflict = conflict_detected or bool(conflicts) or ambiguous_supersession
        effective_evaluations = evaluations
        if (conflicts or ambiguous_supersession) and not any(
            item.verdict == "CONFLICT" for item in evaluations
        ):
            findings = [item.message for item in conflicts]
            if ambiguous_supersession:
                findings.append(
                    "multiple open canonical facts are eligible for supersession; human/auditor resolution required"
                )
            conflict_evaluation = Evaluation(
                id=_stable_id("evaluation", f"structured-conflict:{claim.id}"),
                namespace=claim.namespace,
                information_class=claim.information_class,
                target_id=claim.id,
                evaluator_id="policy:structured-conflict-detector-v2",
                verdict="CONFLICT",
                independent=True,
                confidence=1.0,
                evidence_ids=list(claim.evidence_ids),
                findings=findings,
            )
            effective_evaluations = (*evaluations, conflict_evaluation)

        claim_for_processing = claim
        if len(supersession_candidates) == 1 and not has_conflict:
            claim_for_processing = claim.model_copy(
                update={"supersedes_id": supersession_candidates[0].fact_id}
            )

        for source in sources:
            self.store.put(source)
        for item in evidence:
            self.store.put(item)

        verification = verify_claim(
            claim_for_processing,
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

        superseded_ids: tuple[str, ...] = ()
        if promotion.fact is not None:
            _reject_secret_material(promotion.fact)
            self.store.put(promotion.fact)
            if len(supersession_candidates) == 1:
                superseded = self._supersede_previous(
                    supersession_candidates[0],
                    new_fact=promotion.fact,
                )
                self.store.put(superseded)
                superseded_ids = (superseded.id,)

        return LearningRun(
            verification=verification,
            promotion=promotion,
            stored_fact=promotion.fact,
            conflicts=conflicts,
            superseded_fact_ids=superseded_ids,
        )

    def _supersede_previous(
        self,
        candidate: SupersessionCandidate,
        *,
        new_fact: Fact,
    ) -> Fact:
        previous = self.store.get_latest(candidate.fact_id)
        if not isinstance(previous, Fact):
            raise RuntimeError(f"supersession target disappeared: {candidate.fact_id}")
        new_valid_from = new_fact.temporal.valid_from
        if new_valid_from is None:
            raise RuntimeError("supersession requires new Fact valid_from")
        known_to = new_fact.temporal.known_from or datetime.now(UTC)
        temporal = previous.temporal.model_copy(
            update={
                "valid_to": new_valid_from,
                "known_to": known_to,
            }
        )
        return previous.model_copy(
            update={
                "status": LifecycleStatus.SUPERADO,
                "temporal": temporal,
                "updated_at": datetime.now(UTC),
            }
        )


def _reject_secret_material(record: KnowledgeRecord) -> None:
    if scan_object_for_secrets(record.model_dump(mode="json")):
        raise ValueError(f"secret-like material rejected for {record.record_type}:{record.id}")


def _stable_id(kind: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"sb:{kind}:{digest}"
