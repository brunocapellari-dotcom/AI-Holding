from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AcceptanceCriterion, CriterionStatus, Milestone
from app.schemas.api import ProjectProgress


def project_progress(db: Session, project_id: UUID) -> ProjectProgress:
    milestones = list(
        db.scalars(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.key))
    )
    criteria_total = 0
    criteria_verified = 0
    weighted_numerator = 0.0
    milestone_weight_total = 0

    for milestone in milestones:
        criteria = list(
            db.scalars(
                select(AcceptanceCriterion).where(AcceptanceCriterion.milestone_id == milestone.id)
            )
        )
        milestone_weight_total += milestone.weight
        if not criteria:
            continue
        criterion_weight_total = sum(item.weight for item in criteria)
        verified_weight = sum(
            item.weight for item in criteria if item.status == CriterionStatus.verified
        )
        milestone_ratio = verified_weight / criterion_weight_total if criterion_weight_total else 0.0
        weighted_numerator += milestone_ratio * milestone.weight
        criteria_total += len(criteria)
        criteria_verified += sum(item.status == CriterionStatus.verified for item in criteria)

    pct = (
        round((weighted_numerator / milestone_weight_total) * 100, 2)
        if milestone_weight_total
        else 0.0
    )
    return ProjectProgress(
        project_id=project_id,
        progress_pct=pct,
        milestones_total=len(milestones),
        criteria_total=criteria_total,
        criteria_verified=criteria_verified,
    )
