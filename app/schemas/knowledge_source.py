from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.knowledge_source import (
    SourceAccessMode,
    SourceClass,
    SourceHealth,
    SourceStatus,
)

SOURCE_KEY_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{1,119}$"


class KnowledgeSourceCreate(BaseModel):
    key: str = Field(min_length=2, max_length=120, pattern=SOURCE_KEY_PATTERN)
    name: str = Field(min_length=2, max_length=240)
    base_uri: str = Field(min_length=8, max_length=2000)
    source_class: SourceClass
    access_mode: SourceAccessMode = SourceAccessMode.public
    trust_score: int = Field(default=50, ge=0, le=100)
    license_name: str | None = Field(default=None, max_length=240)
    terms_uri: str | None = Field(default=None, max_length=2000)
    expected_update_minutes: int | None = Field(default=None, ge=5, le=525600)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class KnowledgeSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    base_uri: str
    source_class: SourceClass
    status: SourceStatus
    health_status: SourceHealth
    access_mode: SourceAccessMode
    trust_score: int
    approved_for_fetch: bool
    license_name: str | None
    terms_uri: str | None
    expected_update_minutes: int | None
    last_checked_at: datetime | None
    last_success_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceReview(BaseModel):
    status: SourceStatus
    approved_for_fetch: bool = False
    trust_score: int | None = Field(default=None, ge=0, le=100)
    license_name: str | None = Field(default=None, max_length=240)
    terms_uri: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_approval(self) -> "KnowledgeSourceReview":
        if self.approved_for_fetch and self.status != SourceStatus.approved:
            raise ValueError("approved_for_fetch requires approved source status")
        return self


class KnowledgeSourceHealthOut(BaseModel):
    source_id: UUID
    health_status: SourceHealth
    status_code: int | None = None
    content_type: str | None = None
    checked_at: datetime
    elapsed_ms: int
