from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from second_brain.schemas import Claim, Fact


@dataclass(frozen=True)
class ConflictFinding:
    claim_id: str
    fact_id: str
    assertion_key: str
    existing_value: str
    proposed_value: str
    message: str


def detect_structured_conflicts(
    claim: Claim,
    existing_facts: Iterable[Fact],
) -> tuple[ConflictFinding, ...]:
    """Detect deterministic conflicts only when the extractor supplied a stable assertion key/value.

    Semantic disagreement remains a VERIFIER/KNOWLEDGE_AUDITOR task. This detector deliberately
    avoids declaring contradiction from text similarity alone.
    """
    if not claim.assertion_key or claim.normalized_value is None:
        return ()
    findings: list[ConflictFinding] = []
    for fact in existing_facts:
        if fact.namespace != claim.namespace:
            continue
        if fact.assertion_key != claim.assertion_key or fact.normalized_value is None:
            continue
        if claim.unit and fact.unit and claim.unit.casefold() != fact.unit.casefold():
            continue
        if not _temporal_overlap(claim, fact):
            continue
        if _normalize_value(fact.normalized_value) == _normalize_value(claim.normalized_value):
            continue
        findings.append(
            ConflictFinding(
                claim_id=claim.id,
                fact_id=fact.id,
                assertion_key=claim.assertion_key,
                existing_value=fact.normalized_value,
                proposed_value=claim.normalized_value,
                message="same assertion key has a different value in an overlapping validity window",
            )
        )
    return tuple(findings)


def _temporal_overlap(claim: Claim, fact: Fact) -> bool:
    a = claim.temporal
    b = fact.temporal
    if a.valid_to is not None and b.valid_from is not None:
        try:
            if a.valid_to <= b.valid_from:
                return False
        except TypeError:
            pass
    if b.valid_to is not None and a.valid_from is not None:
        try:
            if b.valid_to <= a.valid_from:
                return False
        except TypeError:
            pass
    return True


def _normalize_value(value: str) -> str:
    return " ".join(value.casefold().split())
