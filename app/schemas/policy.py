from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.entities import RiskLevel
from app.schemas.api import KEY_PATTERN


class ActionType(StrEnum):
    internal_read = "internal_read"
    internal_research = "internal_research"
    internal_write = "internal_write"
    deploy_nonprod = "deploy_nonprod"
    deploy_production = "deploy_production"
    external_communication = "external_communication"
    purchase = "purchase"
    financial_transaction = "financial_transaction"
    credential_change = "credential_change"
    critical_delete = "critical_delete"
    legal_commitment = "legal_commitment"


class PolicyOutcome(StrEnum):
    allow = "allow"
    require_human = "require_human"
    deny = "deny"


class PolicyEvaluationRequest(BaseModel):
    action_key: str = Field(min_length=3, max_length=64, pattern=KEY_PATTERN)
    project_id: UUID
    agent_id: UUID
    action_type: ActionType
    summary: str = Field(min_length=5, max_length=500)
    risk_level: RiskLevel = RiskLevel.low
    irreversible: bool = False
    external_party_effect: bool = False
    sensitive_data: bool = False
    financial_value: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class PolicyEvaluationOut(BaseModel):
    outcome: PolicyOutcome
    required_autonomy: int
    effective_autonomy: int
    reasons: list[str]
    decision_id: UUID | None = None
