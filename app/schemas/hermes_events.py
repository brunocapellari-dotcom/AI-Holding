from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HermesEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=8, max_length=128)
    event_type: str = Field(min_length=3, max_length=80)
    producer: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=120)
    timestamp: datetime
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(min_length=8, max_length=128)
    causation_id: str | None = Field(default=None, min_length=8, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class HermesEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    event_type: str
    producer: str
    project_key: str
    schema_version: str
    correlation_id: str
    causation_id: str | None
    payload: dict[str, object]
    metadata_json: dict[str, object]
    occurred_at: datetime
    received_at: datetime
