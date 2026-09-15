from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from second_brain.schemas import Claim, Fact, LifecycleStatus


@dataclass(frozen=True)
class ConflictFinding:
    claim_id: str
    fact_id: str
    assertion_key: str
    existing_value: str
    proposed_value: str
    message: str


@dataclass(frozen=True)
class SupersessionCandidate:
    claim_id: str
    fact_id: str
    assertion_key: str
    old_value: str
    new_value: str


def detect_structured_conflicts(
    claim: Claim,
    existing_facts: Iterable[Fact],
) -> tuple[ConflictFinding, ...]:
    """Detect deterministic contradictions while allowing newer dated values to supersede.

    Semantic disagreement remains a VERIFIER/KNOWLEDGE_AUDITOR task. A newer assertion for the
    same structured key can supersede an open-ended older Fact rather than being treated as a
    contradiction, but only after the new Claim passes normal canonicalization policy.
    """
    if not claim.assertion_key or claim.normalized_value is None:
        return ()
    findings: list[ConflictFinding] = []
    for fact in existing_facts:
        if not _comparable(claim, fact):
            continue
        if _normalize_value(fact.normalized_value or "") == _normalize_value(claim.normalized_value):
            continue
        if _is_forward_supersession(claim, fact):
            continue
        if not _temporal_overlap(claim, fact):
            continue
        findings.append(
            ConflictFinding(
                claim_id=claim.id,
                fact_id=fact.id,
                assertion_key=claim.assertion_key,
                existing_value=fact.normalized_value or "",
                proposed_value=claim.normalized_value,
                message="same assertion key has a different value in an overlapping validity window",
            )
        )
    return tuple(findings)


def find_supersession_candidates(
    claim: Claim,
    existing_facts: Iterable[Fact],
) -> tuple[SupersessionCandidate, ...]:
    if not claim.assertion_key or claim.normalized_value is None:
        return ()
    candidates: list[SupersessionCandidate] = []
    for fact in existing_facts:
        if not _comparable(claim, fact):
            continue
        if fact.status != LifecycleStatus.CANONICO:
            continue
        if _normalize_value(fact.normalized_value or "") == _normalize_value(claim.normalized_value):
            continue
        if not _is_forward_supersession(claim, fact):
            continue
        candidates.append(
            SupersessionCandidate(
                claim_id=claim.id,
                fact_id=fact.id,
                assertion_key=claim.assertion_key,
                old_value=fact.normalized_value or "",
                new_value=claim.normalized_value,
            )
        )
    candidates.sort(key=lambda item: item.fact_id)
    return tuple(candidates)


def _comparable(claim: Claim, fact: Fact) -> bool:
    if fact.namespace != claim.namespace:
        return False
    if fact.assertion_key != claim.assertion_key or fact.normalized_value is None:
        return False
    if claim.unit and fact.unit and claim.unit.casefold() != fact.unit.casefold():
        return False
    return True


def _is_forward_supersession(claim: Claim, fact: Fact) -> bool:
    claim_start = claim.temporal.valid_from
    fact_start = fact.temporal.valid_from
    return (
        claim_start is not None
        and fact_start is not None
        and claim_start > fact_start
        and fact.temporal.valid_to is None
    )


def _temporal_overlap(claim: Claim, fact: Fact) -> bool:
    a = claim.temporal
    b = fact.temporal
    if a.valid_to is not None and b.valid_from is not None and a.valid_to <= b.valid_from:
        return False
    if b.valid_to is not None and a.valid_from is not None and b.valid_to <= a.valid_from:
        return False
    return True


def _normalize_value(value: str) -> str:
    return " ".join(value.casefold().split())
