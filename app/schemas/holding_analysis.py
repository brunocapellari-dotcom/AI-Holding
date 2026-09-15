from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CompletionGateOut(BaseModel):
    project_id: UUID
    accepted: bool
    progress_pct: float
    criteria_total: int
    criteria_verified: int
    unfinished_tasks: int
    blocking_risks: int
    blocking_alerts: int
    reasons: list[str]


class FinOpsAnomaly(BaseModel):
    currency: str
    current_24h_micros: int = Field(ge=0)
    previous_7d_daily_average_micros: float = Field(ge=0)
    ratio_to_baseline: float | None = Field(default=None, ge=0)
    budget_share_24h: float | None = Field(default=None, ge=0)
    reasons: list[str]


class FinOpsAnalysisOut(BaseModel):
    project_id: UUID
    anomalies: list[FinOpsAnomaly]
    investigation_alerts_opened: int = Field(ge=0)


class VentureGateOut(BaseModel):
    venture_id: UUID
    key: str
    decision: str
    automation_pass: bool
    unit_economics_pass: bool
    risk_pass: bool
    cheap_validation_pass: bool
    evidence_pass: bool
    reasons: list[str]
