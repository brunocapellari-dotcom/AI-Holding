from __future__ import annotations

from dataclasses import dataclass

from second_brain.persistence import SQLiteKnowledgeStore
from second_brain.schemas import Claim, Document, Evaluation, Evidence, Fact, Source
from second_brain.schemas.contracts import KnowledgeRecord


@dataclass(frozen=True)
class ProvenanceTrace:
    root_fact: Fact
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]
    sources: tuple[Source, ...]
    documents: tuple[Document, ...]
    validations: tuple[Evaluation, ...]
    missing_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_ids and bool(self.evidence) and bool(self.sources)

    @property
    def record_ids(self) -> tuple[str, ...]:
        records: tuple[KnowledgeRecord, ...] = (
            self.root_fact,
            *self.claims,
            *self.evidence,
            *self.sources,
            *self.documents,
            *self.validations,
        )
        return tuple(record.id for record in records)


def trace_fact(store: SQLiteKnowledgeStore, fact_id: str) -> ProvenanceTrace:
    root = store.get_latest(fact_id)
    if not isinstance(root, Fact):
        raise KeyError(f"canonical Fact not found: {fact_id}")

    missing: set[str] = set()
    claims = _load_typed(store, root.claim_ids, Claim, missing)
    evidence_ids = set(root.evidence_ids)
    for claim in claims:
        evidence_ids.update(claim.evidence_ids)
    evidence = _load_typed(store, sorted(evidence_ids), Evidence, missing)

    source_ids = {item.source_id for item in evidence}
    if root.provenance.source_id:
        source_ids.add(root.provenance.source_id)
    for claim in claims:
        if claim.provenance.source_id:
            source_ids.add(claim.provenance.source_id)
    sources = _load_typed(store, sorted(source_ids), Source, missing)

    document_ids = {item.document_id for item in evidence if item.document_id}
    if root.provenance.document_id:
        document_ids.add(root.provenance.document_id)
    for claim in claims:
        if claim.provenance.document_id:
            document_ids.add(claim.provenance.document_id)
    documents = _load_typed(store, sorted(document_ids), Document, missing)

    validations = _load_typed(store, root.validation_ids, Evaluation, missing)
    return ProvenanceTrace(
        root_fact=root,
        claims=claims,
        evidence=evidence,
        sources=sources,
        documents=documents,
        validations=validations,
        missing_ids=tuple(sorted(missing)),
    )


def _load_typed[T: KnowledgeRecord](
    store: SQLiteKnowledgeStore,
    record_ids: list[str] | tuple[str, ...],
    expected: type[T],
    missing: set[str],
) -> tuple[T, ...]:
    loaded: list[T] = []
    for record_id in record_ids:
        record = store.get_latest(record_id)
        if not isinstance(record, expected):
            missing.add(record_id)
            continue
        loaded.append(record)
    return tuple(loaded)
