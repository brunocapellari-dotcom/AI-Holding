from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import ReadScope, authorize_read
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def require_operational_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.operational)


def require_governance_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.governance)


def require_financial_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.financial)


def require_security_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.security)


def require_knowledge_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.knowledge)


def require_audit_read(db: DbSession, actor: Actor) -> None:
    authorize_read(db, actor, scope=ReadScope.audit)


def require_full_holding_read(db: DbSession, actor: Actor) -> None:
    for scope in (
        ReadScope.operational,
        ReadScope.governance,
        ReadScope.financial,
        ReadScope.security,
    ):
        authorize_read(db, actor, scope=scope)
