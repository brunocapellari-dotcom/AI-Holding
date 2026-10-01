from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Task, WorkStatus
from app.models.holding import (
    CostEntry,
    HoldingAlert,
    ProjectOperationalProfile,
    RiskRegisterEntry,
    VentureEvaluation,
)
from app.models.holding_evidence import SecurityFinding
from app.schemas.holding_analysis import (
    CompletionGateOut,
    FinOpsAnalysisOut,
    FinOpsAnomaly,
    VentureGateOut,
)
from app.services.progress import project_progress


def completion_gate(db: Session, project_id: UUID) -> CompletionGateOut:
    progress = project_progress(db, project_id)
    unfinished_tasks = list(
        db.scalars(
            select(Task).where(
                Task.project_id == project_id,
                Task.status.notin_([WorkStatus.done, WorkStatus.cancelled]),
            )
        )
    )
    blocking_risks = list(
        db.scalars(
            select(RiskRegisterEntry).where(
                RiskRegisterEntry.project_id == project_id,
                RiskRegisterEntry.status.in_(["open", "mitigating"]),
                RiskRegisterEntry.severity == "critical",
            )
        )
    )
    blocking_alerts = list(
        db.scalars(
            select(HoldingAlert).where(
                HoldingAlert.project_id == project_id,
                HoldingAlert.status == "active",
                HoldingAlert.level.in_(["action_required", "critical"]),
            )
        )
    )
    blocking_security = list(
        db.scalars(
            select(SecurityFinding).where(
                SecurityFinding.project_id == project_id,
                SecurityFinding.status.in_(["open", "mitigating"]),
                SecurityFinding.severity.in_(["high", "critical"]),
            )
        )
    )

    reasons: list[str] = []
    if progress.criteria_total == 0:
        reasons.append("no acceptance criteria exist")
    if progress.criteria_verified != progress.criteria_total:
        reasons.append("not all acceptance criteria are verified")
    if progress.progress_pct != 100.0:
        reasons.append("project progress is below 100%")
    if unfinished_tasks:
        reasons.append("unfinished tasks remain")
    if blocking_risks:
        reasons.append("critical unresolved risks remain")
    if blocking_alerts:
        reasons.append("action-required or critical alerts remain")
    if blocking_security:
        reasons.append("high or critical unresolved security findings remain")

    return CompletionGateOut(
        project_id=project_id,
        accepted=not reasons,
        progress_pct=progress.progress_pct,
        criteria_total=progress.criteria_total,
        criteria_verified=progress.criteria_verified,
        unfinished_tasks=len(unfinished_tasks),
        blocking_risks=len(blocking_risks),
        blocking_alerts=len(blocking_alerts),
        blocking_security_findings=len(blocking_security),
        reasons=reasons,
    )


def analyze_finops(
    db: Session,
    project_id: UUID,
    *,
    now: datetime | None = None,
) -> FinOpsAnalysisOut:
    reference = now or datetime.now(UTC)
    current_start = reference - timedelta(hours=24)
    baseline_start = reference - timedelta(days=8)
    baseline_end = current_start

    costs = list(
        db.scalars(
            select(CostEntry).where(
                CostEntry.project_id == project_id,
                CostEntry.observed_at >= baseline_start,
                CostEntry.observed_at <= reference,
            )
        )
    )
    profile = db.get(ProjectOperationalProfile, project_id)
    currencies = sorted({entry.currency for entry in costs})
    anomalies: list[FinOpsAnomaly] = []
    alerts_opened = 0

    for currency in currencies:
        current = sum(
            entry.amount_micros
            for entry in costs
            if entry.currency == currency and entry.observed_at >= current_start
        )
        baseline_total = sum(
            entry.amount_micros
            for entry in costs
            if entry.currency == currency and baseline_start <= entry.observed_at < baseline_end
        )
        baseline_daily = baseline_total / 7
        ratio = current / baseline_daily if baseline_daily > 0 else None
        budget_share: float | None = None
        if (
            profile is not None
            and profile.budget_micros > 0
            and profile.budget_currency == currency
        ):
            budget_share = current / profile.budget_micros

        reasons: list[str] = []
        if ratio is not None and ratio >= 2.0:
            reasons.append("24h spend is at least 2x the previous 7-day daily average")
        if budget_share is not None and budget_share >= 0.10:
            reasons.append("24h spend consumed at least 10% of the configured budget")
        if not reasons:
            continue

        anomaly = FinOpsAnomaly(
            currency=currency,
            current_24h_micros=current,
            previous_7d_daily_average_micros=baseline_daily,
            ratio_to_baseline=ratio,
            budget_share_24h=budget_share,
            reasons=reasons,
        )
        anomalies.append(anomaly)

        dedupe_key = f"finops-cost-anomaly:{project_id}:{currency}"
        alert = db.scalar(select(HoldingAlert).where(HoldingAlert.dedupe_key == dedupe_key))
        if alert is None:
            alert = HoldingAlert(
                project_id=project_id,
                level="action_required",
                source="finops",
                dedupe_key=dedupe_key,
                title=f"Abnormal cost detected ({currency})",
                details=anomaly.model_dump(),
                status="active",
                occurrences=1,
                last_seen_at=reference,
            )
            db.add(alert)
            alerts_opened += 1
        else:
            alert.level = "action_required"
            alert.details = anomaly.model_dump()
            alert.status = "active"
            alert.occurrences += 1
            alert.last_seen_at = reference

    db.flush()
    return FinOpsAnalysisOut(
        project_id=project_id,
        anomalies=anomalies,
        investigation_alerts_opened=alerts_opened,
    )


def _unit_economics_pass(venture: VentureEvaluation) -> bool:
    explicit = venture.unit_economics.get("plausible_positive")
    if explicit is True:
        return True
    margin = venture.unit_economics.get("gross_margin_target")
    return isinstance(margin, Real) and not isinstance(margin, bool) and float(margin) > 0


def _risk_pass(venture: VentureEvaluation) -> bool:
    explicit = venture.risk_summary.get("controlled")
    if isinstance(explicit, bool):
        return explicit
    if not venture.risk_summary:
        return False
    acceptable = {"controlled", "low", "acceptable", "mitigated"}
    values = [value for value in venture.risk_summary.values() if isinstance(value, str)]
    return bool(values) and all(value.lower() in acceptable for value in values)


def _cheap_validation_pass(venture: VentureEvaluation) -> bool:
    if venture.unit_economics.get("cheap_validation") is True:
        return True
    cap = venture.unit_economics.get("max_validation_cost_micros")
    return (
        isinstance(cap, (int, float))
        and not isinstance(cap, bool)
        and cap >= 0
        and venture.validation_cost_micros <= int(cap)
    )


def evaluate_venture(venture: VentureEvaluation) -> VentureGateOut:
    automation_pass = venture.automation_pct >= 80
    unit_economics_pass = _unit_economics_pass(venture)
    risk_pass = _risk_pass(venture)
    cheap_validation_pass = _cheap_validation_pass(venture)
    evidence_pass = bool(venture.evidence)

    reasons: list[str] = []
    if not automation_pass:
        reasons.append("automation potential is below the 80% gate")
    if not unit_economics_pass:
        reasons.append("positive unit economics are not evidenced")
    if not risk_pass:
        reasons.append("risk is not demonstrated as controlled")
    if not cheap_validation_pass:
        reasons.append("cheap validation is not demonstrated")
    if not evidence_pass:
        reasons.append("gate evidence is missing")

    hard_reject = not automation_pass or venture.risk_summary.get("controlled") is False
    if hard_reject:
        decision = "reject"
    elif not reasons:
        decision = "build"
    else:
        decision = "hold"

    venture.decision = decision
    venture.stage = "gate-reviewed"
    return VentureGateOut(
        venture_id=venture.id,
        key=venture.key,
        decision=decision,
        automation_pass=automation_pass,
        unit_economics_pass=unit_economics_pass,
        risk_pass=risk_pass,
        cheap_validation_pass=cheap_validation_pass,
        evidence_pass=evidence_pass,
        reasons=reasons,
    )
