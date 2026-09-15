from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

StableId = Annotated[str, Field(pattern=r"^sb:[a-z][a-z0-9_-]*:[a-zA-Z0-9._:-]{6,160}$")]
Namespace = Annotated[
    str,
    Field(
        pattern=(
            r"^(shared(?:/[a-z0-9._-]+)*|"
            r"project/[a-z0-9][a-z0-9._-]{1,79}(?:/[a-z0-9._-]+)*)$"
        )
    ),
]


class InformationClass(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class EpistemicNature(StrEnum):
    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    PROJECTED = "PROJECTED"
    INFERRED = "INFERRED"
    STRUCTURAL = "STRUCTURAL"
    QUALITATIVE_SIGNAL = "QUALITATIVE_SIGNAL"


class LifecycleStatus(StrEnum):
    PROPOSTO = "PROPOSTO"
    EM_REVISAO = "EM_REVISÃO"
    VALIDADO = "VALIDADO"
    CANONICO = "CANÔNICO"
    SUPERADO = "SUPERADO"
    REJEITADO = "REJEITADO"
    CONFLITANTE = "CONFLITANTE"
    BAIXA_CONFIANCA = "BAIXA_CONFIANÇA"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class SourceClass(StrEnum):
    PRIMARY = "PRIMARY"
    SPECIALIZED = "SPECIALIZED"
    SECONDARY = "SECONDARY"
    AGGREGATOR = "AGGREGATOR"
    STRUCTURAL = "STRUCTURAL"


class TemporalContext(BaseModel):
    """Bitemporal metadata for world-validity and system-knowledge time."""

    valid_from: datetime | None = None
    valid_to: datetime | None = None
    known_from: datetime | None = None
    known_to: datetime | None = None
    observed_at: datetime | None = None
    reference_date: datetime | None = None
    publication_date: datetime | None = None
    collected_at: datetime | None = None

    @model_validator(mode="after")
    def validate_windows(self) -> "TemporalContext":
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")
        if self.known_from and self.known_to and self.known_to < self.known_from:
            raise ValueError("known_to cannot precede known_from")
        if self.publication_date and self.collected_at and self.collected_at < self.publication_date:
            raise ValueError("collected_at cannot precede publication_date")
        return self


class Provenance(BaseModel):
    source_id: StableId | None = None
    source_uri: str | None = Field(default=None, max_length=3000)
    author_or_institution: str | None = Field(default=None, max_length=500)
    document_id: StableId | None = None
    collector_agent_id: str | None = Field(default=None, max_length=240)
    interpreter_agent_id: str | None = Field(default=None, max_length=240)
    extractor_agent_id: str | None = Field(default=None, max_length=240)
    verifier_agent_id: str | None = Field(default=None, max_length=240)
    method_id: StableId | None = None
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str | None = Field(default=None, max_length=10000)


class RecordBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: StableId
    namespace: Namespace = "shared"
    information_class: InformationClass = InformationClass.INTERNAL
    schema_version: str = Field(default="1.2", pattern=r"^\d+\.\d+$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Source(RecordBase):
    record_type: Literal["Source"] = "Source"
    name: str = Field(min_length=2, max_length=500)
    organization: str | None = Field(default=None, max_length=500)
    canonical_uri: str | None = Field(default=None, max_length=3000)
    source_type: str = Field(min_length=2, max_length=120)
    source_class: SourceClass = SourceClass.SECONDARY
    status: SourceStatus = SourceStatus.CANDIDATE
    authority_class: str | None = Field(default=None, max_length=32)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    license: str | None = Field(default=None, max_length=500)
    terms_reviewed: bool = False
    robots_policy_reviewed: bool = False
    access_method: str | None = Field(default=None, max_length=120)
    approved_for_automated_fetch: bool = False
    approved_for_ingestion: bool = False
    approved_for_canonicalization: bool = False
    independence_group: str | None = Field(default=None, max_length=500)
    primary_source_id: StableId | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def approved_source_must_be_governed(self) -> "Source":
        approvals = (
            self.approved_for_automated_fetch,
            self.approved_for_ingestion,
            self.approved_for_canonicalization,
        )
        if any(approvals) and self.status != SourceStatus.APPROVED:
            raise ValueError("source approvals require status APPROVED")
        if self.approved_for_automated_fetch:
            if not self.terms_reviewed:
                raise ValueError("automated fetch requires terms_reviewed")
            if not self.robots_policy_reviewed:
                raise ValueError("automated fetch requires robots_policy_reviewed")
        if self.approved_for_canonicalization and not self.approved_for_ingestion:
            raise ValueError("canonicalization approval requires ingestion approval")
        return self

    @property
    def independence_key(self) -> str:
        """Key used to avoid counting syndicated copies as independent corroboration."""
        return self.independence_group or self.primary_source_id or self.id


class Document(RecordBase):
    record_type: Literal["Document"] = "Document"
    source_id: StableId
    title: str = Field(min_length=1, max_length=1000)
    uri: str | None = Field(default=None, max_length=3000)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    author_or_institution: str | None = Field(default=None, max_length=500)
    document_date: datetime | None = None
    publication_date: datetime | None = None
    collected_at: datetime | None = None
    license: str | None = Field(default=None, max_length=500)
    metadata: dict[str, object] = Field(default_factory=dict)


class Observation(RecordBase):
    record_type: Literal["Observation"] = "Observation"
    source_id: StableId
    description: str = Field(min_length=1, max_length=30000)
    value: str | None = Field(default=None, max_length=10000)
    nature: EpistemicNature = EpistemicNature.OBSERVED
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    provenance: Provenance


class Evidence(RecordBase):
    record_type: Literal["Evidence"] = "Evidence"
    source_id: StableId
    document_id: StableId | None = None
    locator: str | None = Field(default=None, max_length=2000)
    excerpt_hash: str | None = Field(default=None, max_length=128)
    description: str = Field(min_length=1, max_length=20000)
    observed_value: str | None = Field(default=None, max_length=10000)
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    provenance: Provenance


class Claim(RecordBase):
    record_type: Literal["Claim"] = "Claim"
    statement: str = Field(min_length=5, max_length=30000)
    assertion_key: str | None = Field(default=None, max_length=500)
    normalized_value: str | None = Field(default=None, max_length=10000)
    unit: str | None = Field(default=None, max_length=120)
    status: LifecycleStatus = LifecycleStatus.PROPOSTO
    nature: EpistemicNature = EpistemicNature.STRUCTURAL
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.LOW
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    provenance: Provenance
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    supersedes_id: StableId | None = None
    limitations: list[str] = Field(default_factory=list, max_length=100)


class Fact(RecordBase):
    record_type: Literal["Fact"] = "Fact"
    statement: str = Field(min_length=5, max_length=30000)
    assertion_key: str | None = Field(default=None, max_length=500)
    normalized_value: str | None = Field(default=None, max_length=10000)
    unit: str | None = Field(default=None, max_length=120)
    status: LifecycleStatus
    nature: EpistemicNature
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.LOW
    claim_ids: list[StableId] = Field(min_length=1, max_length=200)
    evidence_ids: list[StableId] = Field(min_length=1, max_length=200)
    validation_ids: list[StableId] = Field(min_length=1, max_length=100)
    provenance: Provenance
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    supersedes_id: StableId | None = None

    @model_validator(mode="after")
    def fact_must_be_institutional(self) -> "Fact":
        if self.status not in {LifecycleStatus.CANONICO, LifecycleStatus.SUPERADO}:
            raise ValueError("Fact status must be CANÔNICO or SUPERADO")
        return self


class Entity(RecordBase):
    record_type: Literal["Entity"] = "Entity"
    entity_type: str = Field(min_length=1, max_length=160)
    canonical_name: str = Field(min_length=1, max_length=1000)
    aliases: list[str] = Field(default_factory=list, max_length=200)
    external_ids: dict[str, str] = Field(default_factory=dict)
    provenance: Provenance | None = None


class Relation(RecordBase):
    record_type: Literal["Relation"] = "Relation"
    subject_id: StableId
    predicate: str = Field(min_length=1, max_length=240)
    object_id: StableId
    status: LifecycleStatus = LifecycleStatus.VALIDADO
    temporal: TemporalContext = Field(default_factory=TemporalContext)
    provenance: Provenance
    causal: bool = False
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def endpoints_differ(self) -> "Relation":
        if self.subject_id == self.object_id and self.predicate not in {"same_as", "version_of"}:
            raise ValueError("self-relations are not allowed for this predicate")
        return self


class Event(RecordBase):
    record_type: Literal["Event"] = "Event"
    title: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=30000)
    status: LifecycleStatus = LifecycleStatus.VALIDADO
    temporal: TemporalContext
    entity_ids: list[StableId] = Field(default_factory=list, max_length=500)
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    provenance: Provenance


class Method(RecordBase):
    record_type: Literal["Method"] = "Method"
    name: str = Field(min_length=2, max_length=500)
    purpose: str = Field(min_length=2, max_length=10000)
    procedure: list[str] = Field(min_length=1, max_length=500)
    assumptions: list[str] = Field(default_factory=list, max_length=200)
    limitations: list[str] = Field(default_factory=list, max_length=200)
    source_ids: list[StableId] = Field(default_factory=list, max_length=200)
    status: LifecycleStatus = LifecycleStatus.VALIDADO


class Model(RecordBase):
    record_type: Literal["Model"] = "Model"
    name: str = Field(min_length=2, max_length=500)
    model_family: str = Field(min_length=2, max_length=240)
    purpose: str = Field(min_length=2, max_length=10000)
    method_ids: list[StableId] = Field(default_factory=list, max_length=200)
    training_or_calibration_window: str | None = Field(default=None, max_length=1000)
    version: str = Field(min_length=1, max_length=120)
    validation_ids: list[StableId] = Field(default_factory=list, max_length=200)
    status: LifecycleStatus = LifecycleStatus.EM_REVISAO


class Skill(RecordBase):
    record_type: Literal["Skill"] = "Skill"
    name: str = Field(min_length=2, max_length=500)
    purpose: str = Field(min_length=2, max_length=10000)
    procedure: list[str] = Field(min_length=1, max_length=500)
    input_contract: dict[str, object] = Field(default_factory=dict)
    output_contract: dict[str, object] = Field(default_factory=dict)
    linked_knowledge_ids: list[StableId] = Field(default_factory=list, max_length=500)
    executable_ref: str | None = Field(default=None, max_length=2000)
    version: str = Field(min_length=1, max_length=120)
    status: LifecycleStatus = LifecycleStatus.VALIDADO


class Decision(RecordBase):
    record_type: Literal["Decision"] = "Decision"
    title: str = Field(min_length=2, max_length=1000)
    decision: str = Field(min_length=2, max_length=30000)
    rationale: str = Field(min_length=2, max_length=30000)
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    related_knowledge_ids: list[StableId] = Field(default_factory=list, max_length=500)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_by: str = Field(min_length=1, max_length=240)


class Evaluation(RecordBase):
    record_type: Literal["Evaluation"] = "Evaluation"
    target_id: StableId
    evaluator_id: str = Field(min_length=1, max_length=240)
    verdict: Literal["APPROVE", "REJECT", "REVIEW", "CONFLICT"]
    independent: bool = True
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    findings: list[str] = Field(default_factory=list, max_length=200)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    human_approval: bool = False


class Learning(RecordBase):
    record_type: Literal["Learning"] = "Learning"
    title: str = Field(min_length=2, max_length=1000)
    lesson: str = Field(min_length=2, max_length=30000)
    originating_project: Namespace
    evidence_ids: list[StableId] = Field(default_factory=list, max_length=200)
    outcome_ids: list[StableId] = Field(default_factory=list, max_length=200)
    applicable_namespaces: list[Namespace] = Field(default_factory=list, max_length=200)
    status: LifecycleStatus = LifecycleStatus.VALIDADO


KnowledgeRecord = (
    Source
    | Document
    | Observation
    | Evidence
    | Claim
    | Fact
    | Entity
    | Relation
    | Event
    | Method
    | Model
    | Skill
    | Decision
    | Evaluation
    | Learning
)


def new_id(kind: str) -> str:
    cleaned = "".join(ch for ch in kind.lower() if ch.isalnum() or ch in "_-").strip("_-")
    if not cleaned:
        raise ValueError("kind must contain at least one identifier character")
    return f"sb:{cleaned}:{uuid4()}"
