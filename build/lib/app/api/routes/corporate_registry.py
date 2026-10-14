from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access_dependencies import require_governance_read
from app.core.actor import ActorContext, get_actor
from app.core.authorization import authorize_mutation
from app.db.session import get_db
from app.models.corporate_registry import (
    ArchitectureDecisionRegistration,
    DataContractRegistration,
    EvaluationRegistration,
    LicenseRegistration,
    ModelRegistration,
    RegistryDirectoryEntry,
    SourceRegistration,
    ToolRegistration,
)
from app.models.entities import Project
from app.schemas.corporate_registry import (
    ArchitectureDecisionRegistryOut,
    ArchitectureDecisionRegistryUpsert,
    DataContractRegistryOut,
    DataContractRegistryUpsert,
    EvaluationRegistryOut,
    EvaluationRegistryUpsert,
    LicenseRegistryOut,
    LicenseRegistryUpsert,
    ModelRegistryOut,
    ModelRegistryUpsert,
    RegistryDirectoryOut,
    SourceRegistryOut,
    SourceRegistryUpsert,
    ToolRegistryOut,
    ToolRegistryUpsert,
)
from app.services.audit import record_audit

router = APIRouter(
    prefix="/holding/registries",
    tags=["corporate-registries"],
    dependencies=[Depends(require_governance_read)],
)
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(limit, 1), 200), min(max(offset, 0), 10_000)


def _require_project(db: Session, project_id: UUID | None) -> None:
    if project_id is not None and db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")


@router.get("", response_model=list[RegistryDirectoryOut])
def registry_directory(db: DbSession) -> list[RegistryDirectoryEntry]:
    return list(
        db.scalars(select(RegistryDirectoryEntry).order_by(RegistryDirectoryEntry.registry_key))
    )


@router.put("/tools/{key}", response_model=ToolRegistryOut)
def upsert_tool(
    key: str,
    payload: ToolRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> ToolRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="tool registry key mismatch")
    row = db.scalar(select(ToolRegistration).where(ToolRegistration.key == key))
    action = "tool_registry.updated"
    if row is None:
        row = ToolRegistration(**payload.model_dump())
        db.add(row)
        action = "tool_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="tool_registry",
        entity_id=str(row.id),
        payload={"key": key, "status": row.status, "capability": row.capability},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/tools", response_model=list[ToolRegistryOut])
def list_tools(
    db: DbSession,
    status: str | None = None,
    capability: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ToolRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(ToolRegistration)
    if status:
        statement = statement.where(ToolRegistration.status == status.strip())
    if capability:
        statement = statement.where(ToolRegistration.capability == capability.strip())
    statement = (
        statement.order_by(ToolRegistration.name).limit(effective_limit).offset(effective_offset)
    )
    return list(db.scalars(statement))


@router.put("/sources/{key}", response_model=SourceRegistryOut)
def upsert_source(
    key: str,
    payload: SourceRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> SourceRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="source registry key mismatch")
    row = db.scalar(select(SourceRegistration).where(SourceRegistration.key == key))
    action = "source_registry.updated"
    if row is None:
        row = SourceRegistration(**payload.model_dump())
        db.add(row)
        action = "source_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="source_registry",
        entity_id=str(row.id),
        payload={"key": key, "status": row.status, "authority": row.authority},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/sources", response_model=list[SourceRegistryOut])
def list_sources(
    db: DbSession,
    status: str | None = None,
    authority: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SourceRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(SourceRegistration)
    if status:
        statement = statement.where(SourceRegistration.status == status.strip())
    if authority:
        statement = statement.where(SourceRegistration.authority == authority.strip())
    statement = (
        statement.order_by(SourceRegistration.name).limit(effective_limit).offset(effective_offset)
    )
    return list(db.scalars(statement))


@router.put("/licenses/{spdx_id}", response_model=LicenseRegistryOut)
def upsert_license(
    spdx_id: str,
    payload: LicenseRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> LicenseRegistration:
    authorize_mutation(db, actor)
    if payload.spdx_id != spdx_id:
        raise HTTPException(status_code=400, detail="license registry SPDX mismatch")
    row = db.scalar(select(LicenseRegistration).where(LicenseRegistration.spdx_id == spdx_id))
    action = "license_registry.updated"
    if row is None:
        row = LicenseRegistration(**payload.model_dump())
        db.add(row)
        action = "license_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="license_registry",
        entity_id=str(row.id),
        payload={"spdx_id": spdx_id, "usage_policy": row.usage_policy},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/licenses", response_model=list[LicenseRegistryOut])
def list_licenses(
    db: DbSession,
    usage_policy: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LicenseRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(LicenseRegistration)
    if usage_policy:
        statement = statement.where(LicenseRegistration.usage_policy == usage_policy.strip())
    statement = (
        statement.order_by(LicenseRegistration.spdx_id)
        .limit(effective_limit)
        .offset(effective_offset)
    )
    return list(db.scalars(statement))


@router.put("/models/{key}", response_model=ModelRegistryOut)
def upsert_model(
    key: str,
    payload: ModelRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> ModelRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="model registry key mismatch")
    row = db.scalar(select(ModelRegistration).where(ModelRegistration.key == key))
    action = "model_registry.updated"
    if row is None:
        row = ModelRegistration(**payload.model_dump())
        db.add(row)
        action = "model_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="model_registry",
        entity_id=str(row.id),
        payload={"key": key, "provider": row.provider, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/models", response_model=list[ModelRegistryOut])
def list_models(
    db: DbSession,
    provider: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ModelRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(ModelRegistration)
    if provider:
        statement = statement.where(ModelRegistration.provider == provider.strip())
    if status:
        statement = statement.where(ModelRegistration.status == status.strip())
    statement = statement.order_by(ModelRegistration.provider, ModelRegistration.model_id)
    statement = statement.limit(effective_limit).offset(effective_offset)
    return list(db.scalars(statement))


@router.put("/evaluations/{key}", response_model=EvaluationRegistryOut)
def upsert_evaluation(
    key: str,
    payload: EvaluationRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> EvaluationRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="evaluation registry key mismatch")
    _require_project(db, payload.project_id)
    row = db.scalar(select(EvaluationRegistration).where(EvaluationRegistration.key == key))
    action = "evaluation_registry.updated"
    if row is None:
        row = EvaluationRegistration(**payload.model_dump())
        db.add(row)
        action = "evaluation_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="evaluation_registry",
        entity_id=str(row.id),
        payload={"key": key, "evaluation_type": row.evaluation_type, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/evaluations", response_model=list[EvaluationRegistryOut])
def list_evaluations(
    db: DbSession,
    project_id: UUID | None = None,
    evaluation_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[EvaluationRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(EvaluationRegistration)
    if project_id is not None:
        statement = statement.where(EvaluationRegistration.project_id == project_id)
    if evaluation_type:
        statement = statement.where(
            EvaluationRegistration.evaluation_type == evaluation_type.strip()
        )
    statement = statement.order_by(EvaluationRegistration.updated_at.desc())
    statement = statement.limit(effective_limit).offset(effective_offset)
    return list(db.scalars(statement))


@router.put("/architecture-decisions/{key}", response_model=ArchitectureDecisionRegistryOut)
def upsert_architecture_decision(
    key: str,
    payload: ArchitectureDecisionRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> ArchitectureDecisionRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="architecture decision registry key mismatch")
    row = db.scalar(
        select(ArchitectureDecisionRegistration).where(ArchitectureDecisionRegistration.key == key)
    )
    action = "architecture_decision_registry.updated"
    if row is None:
        row = ArchitectureDecisionRegistration(**payload.model_dump())
        db.add(row)
        action = "architecture_decision_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="architecture_decision_registry",
        entity_id=str(row.id),
        payload={"key": key, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/architecture-decisions", response_model=list[ArchitectureDecisionRegistryOut])
def list_architecture_decisions(
    db: DbSession,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ArchitectureDecisionRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(ArchitectureDecisionRegistration)
    if status:
        statement = statement.where(ArchitectureDecisionRegistration.status == status.strip())
    statement = statement.order_by(ArchitectureDecisionRegistration.updated_at.desc())
    statement = statement.limit(effective_limit).offset(effective_offset)
    return list(db.scalars(statement))


@router.put("/data-contracts/{key}", response_model=DataContractRegistryOut)
def upsert_data_contract(
    key: str,
    payload: DataContractRegistryUpsert,
    db: DbSession,
    actor: Actor,
) -> DataContractRegistration:
    authorize_mutation(db, actor)
    if payload.key != key:
        raise HTTPException(status_code=400, detail="data contract registry key mismatch")
    _require_project(db, payload.project_id)
    row = db.scalar(select(DataContractRegistration).where(DataContractRegistration.key == key))
    action = "data_contract_registry.updated"
    if row is None:
        row = DataContractRegistration(**payload.model_dump())
        db.add(row)
        action = "data_contract_registry.created"
    else:
        for field, value in payload.model_dump().items():
            setattr(row, field, value)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="data_contract_registry",
        entity_id=str(row.id),
        payload={"key": key, "dataset_key": row.dataset_key, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/data-contracts", response_model=list[DataContractRegistryOut])
def list_data_contracts(
    db: DbSession,
    project_id: UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DataContractRegistration]:
    effective_limit, effective_offset = _page(limit, offset)
    statement = select(DataContractRegistration)
    if project_id is not None:
        statement = statement.where(DataContractRegistration.project_id == project_id)
    if status:
        statement = statement.where(DataContractRegistration.status == status.strip())
    statement = statement.order_by(DataContractRegistration.updated_at.desc())
    statement = statement.limit(effective_limit).offset(effective_offset)
    return list(db.scalars(statement))
