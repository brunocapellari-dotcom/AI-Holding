from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.collector import CollectorStatus
from app.schemas.api import KEY_PATTERN


class CollectorCreate(BaseModel):
    collector_id: str = Field(min_length=2, max_length=100, pattern=KEY_PATTERN)
    source: str = Field(min_length=2, max_length=160)
    collector_type: str = Field(min_length=2, max_length=80)
    frequency_seconds: int | None = Field(default=None, ge=60)
    owner_agent_id: UUID | None = None
    produced_data: dict[str, object] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CollectorActivation(BaseModel):
    enabled: bool


class CollectorReport(BaseModel):
    success: bool
    latency_ms: int | None = Field(default=None, ge=0)
    produced_data: dict[str, object] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_result(self) -> "CollectorReport":
        if self.success and self.error:
            raise ValueError("error is not valid for a successful collection")
        if not self.success and not self.error:
            raise ValueError("error is required for a failed collection")
        return self


class CollectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collector_id: str
    source: str
    collector_type: str
    frequency_seconds: int | None
    last_collected_at: datetime | None
    last_success_at: datetime | None
    status: CollectorStatus
    latency_ms: int | None
    failure_count: int
    consecutive_failures: int
    owner_agent_id: UUID | None
    produced_data: dict[str, object]
    last_error: str | None
    metadata_json: dict[str, object]
    stale: bool
    created_at: datetime
    updated_at: datetime
