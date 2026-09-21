from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import TimestampMixin


class RegistryDirectoryEntry(Base, TimestampMixin):
    __tablename__ = "registry_directory"
    __table_args__ = (
        UniqueConstraint("registry_key", name="uq_registry_directory_key"),
        CheckConstraint(
            "status IN ('active','transitional','candidate','deprecated')",
            name="registry_directory_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_of_truth: Mapped[str] = mapped_column(String(240), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    policy_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    compatibility_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ToolRegistration(Base, TimestampMixin):
    __tablename__ = "tool_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_tool_registry_key"),
        CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name="tool_registry_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    capability: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="holding")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate", index=True)
    version_policy: Mapped[str] = mapped_column(String(120), nullable=False, default="renovate")
    license_spdx: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    repository: Mapped[str | None] = mapped_column(String(240), nullable=True)
    runtime_scope: Mapped[str] = mapped_column(String(120), nullable=False, default="shared")
    security_class: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    capabilities: Mapped[list[object]] = mapped_column(JSON, default=list)
    constraints: Mapped[list[object]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class SourceRegistration(Base, TimestampMixin):
    __tablename__ = "source_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_source_registry_key"),
        CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name="source_registry_status_valid",
        ),
        CheckConstraint(
            "authority IN ('primary','secondary','reference','experimental')",
            name="source_registry_authority_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="research-ai")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate", index=True)
    authority: Mapped[str] = mapped_column(String(24), nullable=False, default="reference", index=True)
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license_spdx: Mapped[str | None] = mapped_column(String(120), nullable=True)
    data_classification: Mapped[str] = mapped_column(String(40), nullable=False, default="public")
    freshness_sla_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provenance_requirements: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    terms_review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class LicenseRegistration(Base, TimestampMixin):
    __tablename__ = "license_registry"
    __table_args__ = (
        UniqueConstraint("spdx_id", name="uq_license_registry_spdx"),
        CheckConstraint(
            "classification IN "
            "('permissive','weak_copyleft','strong_copyleft','source_available',"
            "'proprietary','public_domain','unknown')",
            name="license_registry_classification_valid",
        ),
        CheckConstraint(
            "usage_policy IN ('approved','conditional','restricted','rejected')",
            name="license_registry_usage_policy_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spdx_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    usage_policy: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    conditions: Mapped[list[object]] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ModelRegistration(Base, TimestampMixin):
    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_model_registry_key"),
        CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name="model_registry_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="hermes")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate", index=True)
    intended_uses: Mapped[list[object]] = mapped_column(JSON, default=list)
    prohibited_uses: Mapped[list[object]] = mapped_column(JSON, default=list)
    data_policy: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    cost_policy: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evaluation_gate: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class EvaluationRegistration(Base, TimestampMixin):
    __tablename__ = "evaluation_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_evaluation_registry_key"),
        CheckConstraint(
            "evaluation_type IN "
            "('regression','benchmark','red_team','quality','safety','data_quality','security')",
            name="evaluation_registry_type_valid",
        ),
        CheckConstraint(
            "status IN ('active','candidate','paused','deprecated')",
            name="evaluation_registry_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="holding")
    tool_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    dataset_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gate_policy: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    latest_result: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ArchitectureDecisionRegistration(Base, TimestampMixin):
    __tablename__ = "architecture_decision_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_architecture_decision_registry_key"),
        CheckConstraint(
            "status IN ('proposed','accepted','superseded','rejected','deprecated')",
            name="architecture_decision_registry_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="holding")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed", index=True)
    document_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives: Mapped[list[object]] = mapped_column(JSON, default=list)
    consequences: Mapped[list[object]] = mapped_column(JSON, default=list)
    supersedes_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class DataContractRegistration(Base, TimestampMixin):
    __tablename__ = "data_contract_registry"
    __table_args__ = (
        UniqueConstraint("key", name="uq_data_contract_registry_key"),
        CheckConstraint(
            "status IN ('active','candidate','deprecated','failed')",
            name="data_contract_registry_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    owner_system: Mapped[str] = mapped_column(String(120), nullable=False, default="holding")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate", index=True)
    contract_format: Mapped[str] = mapped_column(String(80), nullable=False, default="holding-data-contract-v1")
    engine: Mapped[str] = mapped_column(String(80), nullable=False, default="native")
    contract_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    required_checks: Mapped[list[object]] = mapped_column(JSON, default=list)
    latest_result: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
