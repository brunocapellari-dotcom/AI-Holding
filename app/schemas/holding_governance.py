from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapabilityAutonomyUpsert(BaseModel):
    capability_key: str = Field(min_length=2, max_length=160)
    autonomy_level: int = Field(ge=0, le=5)
    status: Literal["proposed", "validated", "suspended"] = "proposed"
    authority_scope: dict[str, object] = Field(default_factory=dict)
    constraints: list[object] = Field(default_factory=list)
    evidence: list[object] = Field(default_factory=list)
    rationale: str = Field(min_length=3)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validated_autonomy_requires_evidence(self) -> CapabilityAutonomyUpsert:
        if self.status == "validated" and not self.evidence:
            raise ValueError("validated autonomy requires evidence")
        return self


class CapabilityAutonomyOut(CapabilityAutonomyUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GovernanceReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    score: int = Field(ge=0, le=100)
    findings: list[object]
    evidence: list[object]
    computed_at: datetime
