import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.db.session import get_db
from app.models.entities import Agent, Decision, DecisionStatus, Project
from app.schemas.policy import PolicyEvaluationOut, PolicyEvaluationRequest, PolicyOutcome
from app.services.audit import record_audit
from app.services.policy import evaluate_policy

router = APIRouter(prefix="/policy", tags=["policy"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _fingerprint(payload: PolicyEvaluationRequest) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision_context(
    payload: PolicyEvaluationRequest,
    project: Project,
    agent: Agent,
    fingerprint: str,
) -> str:
    return "\n".join(
        [
            f"Policy fingerprint: {fingerprint}",
            f"Project: {project.key}",
            f"Agent: {agent.key}",
            f"Action: {payload.action_type.value}",
            f"UNTRUSTED REQUEST SUMMARY: {payload.summary}",
        ]
    )


@router.post("/evaluate", response_model=PolicyEvaluationOut)
def evaluate_action(
    payload: PolicyEvaluationRequest,
    db: DbSession,
    actor: Actor,
) -> PolicyEvaluationOut:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    agent = db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")

    result = evaluate_policy(project, agent, payload)
    reasons = list(result.reasons)
    decision_id: UUID | None = None

    if result.outcome == PolicyOutcome.require_human:
        decision_key = f"POLICY_{payload.action_key}"
        fingerprint = _fingerprint(payload)
        context = _decision_context(payload, project, agent, fingerprint)
        existing = db.scalar(
            select(Decision).where(
                Decision.project_id == project.id,
                Decision.key == decision_key,
            )
        )
        if existing:
            if existing.context != context:
                raise HTTPException(
                    status_code=409,
                    detail="action_key was already used for a different policy request",
                )
            decision_id = existing.id
            if existing.status == DecisionStatus.approved:
                result = result.__class__(
                    PolicyOutcome.allow,
                    result.required_autonomy,
                    result.effective_autonomy,
                    tuple(reasons + ["matching human approval exists"]),
                )
            elif existing.status in {DecisionStatus.rejected, DecisionStatus.superseded}:
                result = result.__class__(
                    PolicyOutcome.deny,
                    result.required_autonomy,
                    result.effective_autonomy,
                    tuple(reasons + [f"human decision is {existing.status.value}"]),
                )
        else:
            recommendation = (
                "Human approval required by deterministic policy: " + "; ".join(reasons)
            )
            decision = Decision(
                key=decision_key,
                project_id=project.id,
                title=f"Policy approval: {payload.action_type.value}",
                context=context,
                recommendation=recommendation,
                risk_level=payload.risk_level,
                requires_human=True,
                options=[{"outcome": "approved"}, {"outcome": "rejected"}],
            )
            db.add(decision)
            db.flush()
            decision_id = decision.id
            record_audit(
                db,
                actor=actor,
                action="policy.human_gate_created",
                entity_type="decision",
                entity_id=str(decision.id),
                payload={
                    "action_key": payload.action_key,
                    "action_type": payload.action_type.value,
                    "fingerprint": fingerprint,
                },
            )

    record_audit(
        db,
        actor=actor,
        action="policy.evaluated",
        entity_type="project",
        entity_id=str(project.id),
        payload={
            "action_key": payload.action_key,
            "action_type": payload.action_type.value,
            "agent_id": str(agent.id),
            "outcome": result.outcome.value,
            "required_autonomy": result.required_autonomy,
            "effective_autonomy": result.effective_autonomy,
        },
    )
    db.commit()

    return PolicyEvaluationOut(
        outcome=result.outcome,
        required_autonomy=result.required_autonomy,
        effective_autonomy=result.effective_autonomy,
        reasons=list(result.reasons),
        decision_id=decision_id,
    )
