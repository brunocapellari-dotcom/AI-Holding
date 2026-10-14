from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RegistryStatus = Literal["approved", "candidate", "restricted", "deprecated", "rejected"]


class RegistryDirectoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    registry_key: str
    name: str
    owner_system: str
    source_of_truth: str
    schema_version: str
    status: Literal["active", "transitional", "candidate", "deprecated"]
    policy_json: dict[str, object]
    compatibility_json: dict[str, object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ToolRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=160)
    capability: str = Field(min_length=2, max_length=160)
    owner_system: str = Field(default="holding", min_length=2, max_length=120)
    status: RegistryStatus = "candidate"
    version_policy: str = Field(default="renovate", min_length=2, max_length=120)
    license_spdx: str | None = Field(default=None, max_length=120)
    repository: str | None = Field(default=None, max_length=240)
    runtime_scope: str = Field(default="shared", min_length=2, max_length=120)
    security_class: str = Field(default="internal", min_length=2, max_length=40)
    capabilities: list[object] = Field(default_factory=list)
    constraints: list[object] = Field(default_factory=list)
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class ToolRegistryOut(ToolRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class SourceRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=160)
    name: str = Field(min_length=2, max_length=200)
    source_type: str = Field(min_length=2, max_length=80)
    owner_system: str = Field(default="research-ai", min_length=2, max_length=120)
    status: RegistryStatus = "candidate"
    authority: Literal["primary", "secondary", "reference", "experimental"] = "reference"
    endpoint: str | None = Field(default=None, max_length=500)
    license_spdx: str | None = Field(default=None, max_length=120)
    data_classification: str = Field(default="public", min_length=2, max_length=40)
    freshness_sla_seconds: int | None = Field(default=None, gt=0)
    provenance_requirements: dict[str, object] = Field(default_factory=dict)
    terms_review_status: str = Field(default="pending", min_length=2, max_length=40)
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class SourceRegistryOut(SourceRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class LicenseRegistryUpsert(BaseModel):
    spdx_id: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=200)
    classification: Literal[
        "permissive",
        "weak_copyleft",
        "strong_copyleft",
        "source_available",
        "proprietary",
        "public_domain",
        "unknown",
    ]
    usage_policy: Literal["approved", "conditional", "restricted", "rejected"]
    conditions: list[object] = Field(default_factory=list)
    source_url: str | None = Field(default=None, max_length=500)
    reviewed_by: str | None = Field(default=None, max_length=160)
    reviewed_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reviewed_policy_has_reviewer(self) -> LicenseRegistryUpsert:
        if (
            self.usage_policy != "rejected"
            and self.reviewed_at is not None
            and not self.reviewed_by
        ):
            raise ValueError("reviewed license policy requires reviewed_by")
        return self


class LicenseRegistryOut(LicenseRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ModelRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=160)
    provider: str = Field(min_length=2, max_length=120)
    model_id: str = Field(min_length=2, max_length=200)
    owner_system: str = Field(default="hermes", min_length=2, max_length=120)
    status: RegistryStatus = "candidate"
    intended_uses: list[object] = Field(default_factory=list)
    prohibited_uses: list[object] = Field(default_factory=list)
    data_policy: dict[str, object] = Field(default_factory=dict)
    cost_policy: dict[str, object] = Field(default_factory=dict)
    evaluation_gate: dict[str, object] = Field(default_factory=dict)
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class ModelRegistryOut(ModelRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class EvaluationRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=160)
    project_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    evaluation_type: Literal[
        "regression", "benchmark", "red_team", "quality", "safety", "data_quality", "security"
    ]
    owner_system: str = Field(default="holding", min_length=2, max_length=120)
    tool_key: str | None = Field(default=None, max_length=120)
    status: Literal["active", "candidate", "paused", "deprecated"] = "active"
    dataset_ref: str | None = Field(default=None, max_length=500)
    gate_policy: dict[str, object] = Field(default_factory=dict)
    latest_result: dict[str, object] = Field(default_factory=dict)
    last_run_at: datetime | None = None
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class EvaluationRegistryOut(EvaluationRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ArchitectureDecisionRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=3, max_length=240)
    owner_system: str = Field(default="holding", min_length=2, max_length=120)
    status: Literal["proposed", "accepted", "superseded", "rejected", "deprecated"] = "proposed"
    document_ref: str = Field(min_length=3, max_length=500)
    rationale: str = Field(min_length=3)
    alternatives: list[object] = Field(default_factory=list)
    consequences: list[object] = Field(default_factory=list)
    supersedes_key: str | None = Field(default=None, max_length=120)
    decided_at: datetime | None = None
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def final_decisions_require_timestamp(self) -> ArchitectureDecisionRegistryUpsert:
        if (
            self.status in {"accepted", "superseded", "rejected", "deprecated"}
            and self.decided_at is None
        ):
            raise ValueError("final architecture decision status requires decided_at")
        return self


class ArchitectureDecisionRegistryOut(ArchitectureDecisionRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class DataContractRegistryUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=160)
    project_id: UUID | None = None
    dataset_key: str = Field(min_length=2, max_length=200)
    owner_system: str = Field(default="holding", min_length=2, max_length=120)
    status: Literal["active", "candidate", "deprecated", "failed"] = "candidate"
    contract_format: str = Field(default="holding-data-contract-v1", min_length=2, max_length=80)
    engine: str = Field(default="native", min_length=2, max_length=80)
    contract_ref: str = Field(min_length=3, max_length=500)
    version: str = Field(min_length=1, max_length=80)
    required_checks: list[object] = Field(default_factory=list)
    latest_result: dict[str, object] = Field(default_factory=dict)
    last_verified_at: datetime | None = None
    blocking: bool = True
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DataContractRegistryOut(DataContractRegistryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
