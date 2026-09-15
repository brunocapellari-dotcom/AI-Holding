from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from second_brain.schemas import Fact, InformationClass, Learning, LifecycleStatus, Method, Skill
from second_brain.schemas.contracts import KnowledgeRecord
from second_brain.store import KnowledgeStore

_TOKEN = re.compile(r"[A-Za-zÀ-ÿ0-9_]{3,}")
_CLASS_RANK = {
    InformationClass.PUBLIC: 0,
    InformationClass.INTERNAL: 1,
    InformationClass.CONFIDENTIAL: 2,
    InformationClass.RESTRICTED: 3,
}


@dataclass(frozen=True)
class AccessPolicy:
    allowed_namespace_prefixes: tuple[str, ...]
    max_information_class: InformationClass = InformationClass.INTERNAL
    allow_shared: bool = True


@dataclass(frozen=True)
class RetrievedRecord:
    record: KnowledgeRecord
    score: float


def can_read(record: KnowledgeRecord, policy: AccessPolicy) -> bool:
    if _CLASS_RANK[record.information_class] > _CLASS_RANK[policy.max_information_class]:
        return False
    if record.namespace == "shared" or record.namespace.startswith("shared/"):
        return policy.allow_shared
    return any(_namespace_matches(record.namespace, prefix) for prefix in policy.allowed_namespace_prefixes)


def retrieve_context(
    store: KnowledgeStore,
    query: str,
    *,
    policy: AccessPolicy,
    valid_at: datetime | None = None,
    known_at: datetime | None = None,
    limit: int = 12,
) -> tuple[RetrievedRecord, ...]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    now = datetime.now(UTC)
    valid_time = valid_at or now
    known_time = known_at or now
    candidates: list[KnowledgeRecord] = list(
        store.query_facts_as_of(valid_at=valid_time, known_at=known_time)
    )
    for record in store.all_latest():
        if isinstance(record, Fact):
            continue
        if isinstance(record, (Method, Skill, Learning)) and record.status in {
            LifecycleStatus.VALIDADO,
            LifecycleStatus.CANONICO,
        }:
            candidates.append(record)

    query_tokens = _tokens(query)
    ranked: list[RetrievedRecord] = []
    for record in candidates:
        if not can_read(record, policy):
            continue
        score = _score(query_tokens, _record_text(record))
        if score > 0 or not query_tokens:
            ranked.append(RetrievedRecord(record=record, score=score))
    ranked.sort(key=lambda item: (-item.score, item.record.id))
    return tuple(ranked[:limit])


def _record_text(record: KnowledgeRecord) -> str:
    fields: list[str] = [record.id, record.namespace, record.record_type]
    for attribute in (
        "statement",
        "assertion_key",
        "normalized_value",
        "title",
        "name",
        "purpose",
        "lesson",
        "decision",
        "rationale",
    ):
        value = getattr(record, attribute, None)
        if isinstance(value, str):
            fields.append(value)
    return " ".join(fields)


def _tokens(text: str) -> set[str]:
    return {match.group(0).casefold() for match in _TOKEN.finditer(text)}


def _score(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 1.0
    haystack = _tokens(text)
    overlap = len(query_tokens & haystack)
    if overlap == 0:
        return 0.0
    return overlap / len(query_tokens)


def _namespace_matches(namespace: str, prefix: str) -> bool:
    return namespace == prefix or namespace.startswith(f"{prefix}/")
