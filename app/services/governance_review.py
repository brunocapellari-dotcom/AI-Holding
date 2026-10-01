from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Project
from app.models.holding_governance import CapabilityAutonomy, GovernanceReviewSnapshot
from app.schemas.holding_governance import GovernanceReviewOut


def review_project_governance(db: Session, project_id: UUID) -> GovernanceReviewOut:
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")

    entries = list(
        db.scalars(select(CapabilityAutonomy).where(CapabilityAutonomy.project_id == project_id))
    )
    by_key = {entry.capability_key: entry for entry in entries}
    declared = project.metadata_json.get("capabilities", [])
    if not isinstance(declared, list):
        declared = []
    declared_keys = [item for item in declared if isinstance(item, str)]

    score = 100
    findings: list[object] = []
    evidence: list[object] = []

    if not declared_keys:
        score -= 10
        findings.append(
            {
                "kind": "capabilities_undeclared",
                "message": "project metadata has no canonical capability list",
            }
        )

    for capability_key in declared_keys:
        entry = by_key.get(capability_key)
        if entry is None:
            score -= 15
            findings.append(
                {
                    "kind": "autonomy_missing",
                    "capability_key": capability_key,
                }
            )
            continue
        evidence.append(
            {
                "capability_key": capability_key,
                "autonomy_level": entry.autonomy_level,
                "status": entry.status,
                "evidence_count": len(entry.evidence),
            }
        )

    for entry in entries:
        if entry.status == "suspended":
            score -= 10
            findings.append(
                {
                    "kind": "autonomy_suspended",
                    "capability_key": entry.capability_key,
                }
            )
        if entry.status == "validated" and not entry.evidence:
            score -= 25
            findings.append(
                {
                    "kind": "validated_without_evidence",
                    "capability_key": entry.capability_key,
                }
            )
        if entry.autonomy_level >= 4 and not entry.constraints:
            score -= 20
            findings.append(
                {
                    "kind": "high_autonomy_without_constraints",
                    "capability_key": entry.capability_key,
                    "autonomy_level": entry.autonomy_level,
                }
            )
        if entry.autonomy_level >= 4 and not entry.evidence:
            score -= 20
            findings.append(
                {
                    "kind": "high_autonomy_without_evidence",
                    "capability_key": entry.capability_key,
                    "autonomy_level": entry.autonomy_level,
                }
            )

    score = max(0, score)
    snapshot = GovernanceReviewSnapshot(
        project_id=project_id,
        score=score,
        findings=findings,
        evidence=evidence,
    )
    db.add(snapshot)
    db.flush()
    return GovernanceReviewOut.model_validate(snapshot)
