from __future__ import annotations

from enum import StrEnum


class KnowledgeAgentRole(StrEnum):
    KNOWLEDGE_DIRECTOR = "KNOWLEDGE_DIRECTOR_AI"
    INGESTION = "INGESTION_AI"
    VIDEO_LEARNING = "VIDEO_LEARNING_AI"
    DOCUMENT_READER = "DOCUMENT_READER_AI"
    SCIENTIFIC_RESEARCH = "SCIENTIFIC_RESEARCH_AI"
    NEWS_LEARNING = "NEWS_LEARNING_AI"
    CLAIM_EXTRACTOR = "CLAIM_EXTRACTOR_AI"
    VERIFIER = "VERIFIER_AI"
    KNOWLEDGE_AUDITOR = "KNOWLEDGE_AUDITOR_AI"
    CURATOR = "CURATOR_AI"
    PROVENANCE = "PROVENANCE_AI"


class KnowledgeCapability(StrEnum):
    COORDINATE = "coordinate"
    COLLECT = "collect"
    INTERPRET = "interpret"
    EXTRACT_CLAIM = "extract_claim"
    VERIFY = "verify"
    VALIDATE = "validate"
    CURATE = "curate"
    WRITE_PROVENANCE = "write_provenance"
    PROPOSE_CANONICALIZATION = "propose_canonicalization"


_CAPABILITIES: dict[KnowledgeAgentRole, frozenset[KnowledgeCapability]] = {
    KnowledgeAgentRole.KNOWLEDGE_DIRECTOR: frozenset(
        {KnowledgeCapability.COORDINATE, KnowledgeCapability.PROPOSE_CANONICALIZATION}
    ),
    KnowledgeAgentRole.INGESTION: frozenset(
        {KnowledgeCapability.COLLECT, KnowledgeCapability.WRITE_PROVENANCE}
    ),
    KnowledgeAgentRole.VIDEO_LEARNING: frozenset(
        {
            KnowledgeCapability.COLLECT,
            KnowledgeCapability.INTERPRET,
            KnowledgeCapability.WRITE_PROVENANCE,
        }
    ),
    KnowledgeAgentRole.DOCUMENT_READER: frozenset(
        {
            KnowledgeCapability.COLLECT,
            KnowledgeCapability.INTERPRET,
            KnowledgeCapability.WRITE_PROVENANCE,
        }
    ),
    KnowledgeAgentRole.SCIENTIFIC_RESEARCH: frozenset(
        {
            KnowledgeCapability.COLLECT,
            KnowledgeCapability.INTERPRET,
            KnowledgeCapability.WRITE_PROVENANCE,
        }
    ),
    KnowledgeAgentRole.NEWS_LEARNING: frozenset(
        {
            KnowledgeCapability.COLLECT,
            KnowledgeCapability.INTERPRET,
            KnowledgeCapability.WRITE_PROVENANCE,
        }
    ),
    KnowledgeAgentRole.CLAIM_EXTRACTOR: frozenset(
        {KnowledgeCapability.EXTRACT_CLAIM, KnowledgeCapability.WRITE_PROVENANCE}
    ),
    KnowledgeAgentRole.VERIFIER: frozenset(
        {KnowledgeCapability.VERIFY, KnowledgeCapability.WRITE_PROVENANCE}
    ),
    KnowledgeAgentRole.KNOWLEDGE_AUDITOR: frozenset(
        {
            KnowledgeCapability.VALIDATE,
            KnowledgeCapability.PROPOSE_CANONICALIZATION,
            KnowledgeCapability.WRITE_PROVENANCE,
        }
    ),
    KnowledgeAgentRole.CURATOR: frozenset(
        {KnowledgeCapability.CURATE, KnowledgeCapability.WRITE_PROVENANCE}
    ),
    KnowledgeAgentRole.PROVENANCE: frozenset({KnowledgeCapability.WRITE_PROVENANCE}),
}


def capabilities_for(role: KnowledgeAgentRole) -> frozenset[KnowledgeCapability]:
    return _CAPABILITIES[role]


def require_capability(role: KnowledgeAgentRole, capability: KnowledgeCapability) -> None:
    if capability not in capabilities_for(role):
        raise PermissionError(f"{role.value} cannot perform {capability.value}")
