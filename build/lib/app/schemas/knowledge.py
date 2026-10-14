from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.knowledge import EpistemicStatus, KnowledgeLifecycle, OutcomeVerdict

NAMESPACE_PATTERN = r"^[a-z0-9][a-z0-9._-]{1,119}$"


class EvidenceRef(BaseModel):
    source: str = Field(min_length=2, max_length=240)
    uri: str | None = Field(default=None, max_length=2000)
    locator: str | None = Field(default=None, max_length=1000)
    captured_at: datetime | None = None
    checksum: str | None = Field(default=None, max_length=128)
    metadata: dict[str, object] = Field(default_factory=dict)


class KnowledgeClaimIngest(BaseModel):
    namespace: str = Field(min_length=2, max_length=120, pattern=NAMESPACE_PATTERN)
    project_id: UUID | None = None
    created_by_agent_id: UUID | None = None
    statement: str = Field(min_length=5, max_length=20000)
    epistemic_status: EpistemicStatus = EpistemicStatus.structural
    confidence: int = Field(default=50, ge=0, le=100)
    source_name: str = Field(min_length=2, max_length=240)
    source_uri: str | None = Field(default=None, max_length=2000)
    source_published_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=50)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_validity_window(self) -> "KnowledgeClaimIngest":
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be greater than or equal to valid_from")
        return self


class KnowledgeClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    namespace: str
    project_id: UUID | None
    created_by_agent_id: UUID | None
    statement: str
    fingerprint: str
    epistemic_status: EpistemicStatus
    lifecycle_status: KnowledgeLifecycle
    confidence: int
    source_name: str
    source_uri: str | None
    source_published_at: datetime | None
    valid_from: datetime | None
    valid_until: datetime | None
    evidence: list[object]
    tags: list[object]
    metadata_json: dict[str, object]
    supersedes_id: UUID | None
    promoted_at: datetime | None
    obsidian_path: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeIngestResult(BaseModel):
    claim: KnowledgeClaimOut
    created: bool
    merged_evidence: int = 0


class KnowledgeTransition(BaseModel):
    lifecycle_status: KnowledgeLifecycle
    supersedes_id: UUID | None = None


class KnowledgeOutcomeCreate(BaseModel):
    project_id: UUID | None = None
    created_by_agent_id: UUID | None = None
    verdict: OutcomeVerdict
    observed_result: str = Field(min_length=3, max_length=20000)
    error_metric: float | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list, max_length=50)
    metadata_json: dict[str, object] = Field(default_factory=dict)
    evaluated_at: datetime | None = None


class KnowledgeOutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    project_id: UUID | None
    created_by_agent_id: UUID | None
    verdict: OutcomeVerdict
    observed_result: str
    error_metric: float | None
    evidence: list[object]
    metadata_json: dict[str, object]
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime


class KnowledgeMarkdownOut(BaseModel):
    claim_id: UUID
    markdown: str


class KnowledgeExportOut(BaseModel):
    claim_id: UUID
    relative_path: str
    bytes_written: int
