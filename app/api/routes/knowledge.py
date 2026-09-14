from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.entities import Agent, Project
from app.models.knowledge import KnowledgeClaim, KnowledgeLifecycle, KnowledgeOutcome
from app.schemas.knowledge import (
    KnowledgeClaimIngest,
    KnowledgeClaimOut,
    KnowledgeExportOut,
    KnowledgeIngestResult,
    KnowledgeMarkdownOut,
    KnowledgeOutcomeCreate,
    KnowledgeOutcomeOut,
    KnowledgeTransition,
)
from app.services.audit import record_audit
from app.services.knowledge import (
    export_claim_to_obsidian,
    ingest_claim,
    record_outcome,
    render_claim_markdown,
    retrieve_context,
    transition_claim,
)
from app.services.knowledge_gap import find_knowledge_gaps
from app.services.knowledge_outcome_review import find_outcome_review_candidates

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _claim_or_404(db: Session, claim_id: UUID) -> KnowledgeClaim:
    claim = db.get(KnowledgeClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="knowledge claim not found")
    return claim


def _validate_references(db: Session, project_id: UUID | None, agent_id: UUID | None) -> None:
    if project_id is not None and db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    if agent_id is not None and db.get(Agent, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")


@router.get("/claims", response_model=list[KnowledgeClaimOut])
def list_claims(
    db: DbSession,
    namespace: str | None = None,
    project_id: UUID | None = None,
    lifecycle_status: KnowledgeLifecycle | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[KnowledgeClaim]:
    statement = select(KnowledgeClaim)
    if namespace:
        statement = statement.where(KnowledgeClaim.namespace == namespace)
    if project_id:
        statement = statement.where(KnowledgeClaim.project_id == project_id)
    if lifecycle_status:
        statement = statement.where(KnowledgeClaim.lifecycle_status == lifecycle_status.value)
    if q:
        statement = statement.where(KnowledgeClaim.statement.ilike(f"%{q.strip()}%"))
    statement = statement.order_by(KnowledgeClaim.updated_at.desc()).limit(min(max(limit, 1), 500))
    statement = statement.offset(max(offset, 0))
    return list(db.scalars(statement))


@router.get("/gaps", response_model=list[KnowledgeClaimOut])
def get_knowledge_gaps(
    db: DbSession,
    namespace: str | None = None,
    project_id: UUID | None = None,
    limit: int = 100,
) -> list[KnowledgeClaim]:
    return find_knowledge_gaps(
        db,
        namespace=namespace,
        project_id=project_id,
        limit=limit,
    )


@router.get("/outcome-review", response_model=list[KnowledgeClaimOut])
def get_outcome_review_queue(
    db: DbSession,
    namespace: str | None = None,
    project_id: UUID | None = None,
    limit: int = 100,
) -> list[KnowledgeClaim]:
    return find_outcome_review_candidates(
        db,
        namespace=namespace,
        project_id=project_id,
        limit=limit,
    )


@router.get("/claims/{claim_id}", response_model=KnowledgeClaimOut)
def get_claim(claim_id: UUID, db: DbSession) -> KnowledgeClaim:
    return _claim_or_404(db, claim_id)


@router.post(
    "/claims",
    response_model=KnowledgeIngestResult,
    status_code=status.HTTP_201_CREATED,
)
def create_or_merge_claim(
    payload: KnowledgeClaimIngest,
    db: DbSession,
    actor: Actor,
) -> KnowledgeIngestResult:
    bound_agent = authorize_mutation(
        db,
        actor,
        permission=AgentPermission.submit_knowledge,
        expected_agent_id=payload.created_by_agent_id,
    )
    _validate_references(db, payload.project_id, payload.created_by_agent_id)
    try:
        claim, created, merged_evidence = ingest_claim(
            db,
            payload,
            created_by_agent_id=(bound_agent.id if bound_agent else payload.created_by_agent_id),
        )
        record_audit(
            db,
            actor=actor,
            action="knowledge.ingested" if created else "knowledge.merged",
            entity_type="knowledge_claim",
            entity_id=str(claim.id),
            payload={
                "namespace": claim.namespace,
                "fingerprint": claim.fingerprint,
                "merged_evidence": merged_evidence,
            },
        )
        db.commit()
        db.refresh(claim)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="knowledge claim conflicts with stored state",
        ) from exc
    return KnowledgeIngestResult(
        claim=KnowledgeClaimOut.model_validate(claim),
        created=created,
        merged_evidence=merged_evidence,
    )


@router.post("/claims/{claim_id}/transition", response_model=KnowledgeClaimOut)
def promote_claim(
    claim_id: UUID,
    payload: KnowledgeTransition,
    db: DbSession,
    actor: Actor,
) -> KnowledgeClaim:
    authorize_mutation(db, actor, permission=AgentPermission.promote_knowledge)
    claim = _claim_or_404(db, claim_id)
    old_status = claim.lifecycle_status
    try:
        transition_claim(
            db,
            claim,
            target=payload.lifecycle_status,
            supersedes_id=payload.supersedes_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit(
        db,
        actor=actor,
        action="knowledge.transitioned",
        entity_type="knowledge_claim",
        entity_id=str(claim.id),
        payload={
            "from": old_status,
            "to": claim.lifecycle_status,
            "supersedes_id": (str(payload.supersedes_id) if payload.supersedes_id else None),
        },
    )
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/context", response_model=list[KnowledgeClaimOut])
def get_context(
    namespace: str,
    db: DbSession,
    q: str | None = None,
    project_id: UUID | None = None,
    limit: int = 20,
) -> list[KnowledgeClaim]:
    return retrieve_context(
        db,
        namespace=namespace,
        q=q,
        project_id=project_id,
        limit=limit,
    )


@router.post(
    "/claims/{claim_id}/outcomes",
    response_model=KnowledgeOutcomeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_outcome(
    claim_id: UUID,
    payload: KnowledgeOutcomeCreate,
    db: DbSession,
    actor: Actor,
) -> KnowledgeOutcome:
    bound_agent = authorize_mutation(
        db,
        actor,
        permission=AgentPermission.submit_knowledge_outcome,
        expected_agent_id=payload.created_by_agent_id,
    )
    _validate_references(db, payload.project_id, payload.created_by_agent_id)
    claim = _claim_or_404(db, claim_id)
    outcome = record_outcome(
        db,
        claim,
        payload,
        created_by_agent_id=(bound_agent.id if bound_agent else payload.created_by_agent_id),
    )
    record_audit(
        db,
        actor=actor,
        action="knowledge.outcome_recorded",
        entity_type="knowledge_claim",
        entity_id=str(claim.id),
        payload={"verdict": outcome.verdict, "outcome_id": str(outcome.id)},
    )
    db.commit()
    db.refresh(outcome)
    return outcome


@router.get("/claims/{claim_id}/outcomes", response_model=list[KnowledgeOutcomeOut])
def list_outcomes(claim_id: UUID, db: DbSession) -> list[KnowledgeOutcome]:
    _claim_or_404(db, claim_id)
    statement = (
        select(KnowledgeOutcome)
        .where(KnowledgeOutcome.claim_id == claim_id)
        .order_by(KnowledgeOutcome.evaluated_at.desc())
    )
    return list(db.scalars(statement))


@router.get("/claims/{claim_id}/markdown", response_model=KnowledgeMarkdownOut)
def render_markdown(claim_id: UUID, db: DbSession) -> KnowledgeMarkdownOut:
    claim = _claim_or_404(db, claim_id)
    return KnowledgeMarkdownOut(
        claim_id=claim.id,
        markdown=render_claim_markdown(claim),
    )


@router.post("/claims/{claim_id}/export", response_model=KnowledgeExportOut)
def export_to_obsidian(
    claim_id: UUID,
    db: DbSession,
    actor: Actor,
) -> KnowledgeExportOut:
    authorize_mutation(db, actor, permission=AgentPermission.export_knowledge)
    claim = _claim_or_404(db, claim_id)
    try:
        relative_path, bytes_written = export_claim_to_obsidian(claim)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit(
        db,
        actor=actor,
        action="knowledge.exported_to_obsidian",
        entity_type="knowledge_claim",
        entity_id=str(claim.id),
        payload={"relative_path": relative_path, "bytes_written": bytes_written},
    )
    db.commit()
    db.refresh(claim)
    return KnowledgeExportOut(
        claim_id=claim.id,
        relative_path=relative_path,
        bytes_written=bytes_written,
    )
