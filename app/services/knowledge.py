from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import (
    KnowledgeClaim,
    KnowledgeLifecycle,
    KnowledgeOutcome,
)
from app.schemas.knowledge import KnowledgeClaimIngest, KnowledgeOutcomeCreate

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    KnowledgeLifecycle.raw.value: {
        KnowledgeLifecycle.candidate.value,
        KnowledgeLifecycle.superseded.value,
    },
    KnowledgeLifecycle.candidate.value: {
        KnowledgeLifecycle.validated.value,
        KnowledgeLifecycle.superseded.value,
    },
    KnowledgeLifecycle.validated.value: {
        KnowledgeLifecycle.canonical.value,
        KnowledgeLifecycle.superseded.value,
    },
    KnowledgeLifecycle.canonical.value: {KnowledgeLifecycle.superseded.value},
    KnowledgeLifecycle.superseded.value: set(),
}


def normalize_statement(statement: str) -> str:
    return re.sub(r"\s+", " ", statement.strip().lower())


def fingerprint_statement(statement: str) -> str:
    return hashlib.sha256(normalize_statement(statement).encode("utf-8")).hexdigest()


def _merge_json_objects(
    existing: list[object], incoming: Iterable[object]
) -> tuple[list[object], int]:
    merged = list(existing or [])
    seen = {json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) for item in merged}
    added = 0
    for item in incoming:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        if key not in seen:
            seen.add(key)
            merged.append(item)
            added += 1
    return merged, added


def ingest_claim(
    db: Session,
    payload: KnowledgeClaimIngest,
    *,
    created_by_agent_id: UUID | None = None,
) -> tuple[KnowledgeClaim, bool, int]:
    fingerprint = fingerprint_statement(payload.statement)
    existing = db.scalar(
        select(KnowledgeClaim).where(
            KnowledgeClaim.namespace == payload.namespace,
            KnowledgeClaim.fingerprint == fingerprint,
        )
    )
    evidence = [item.model_dump(mode="json") for item in payload.evidence]
    tags = list(dict.fromkeys(tag.strip() for tag in payload.tags if tag.strip()))
    now = datetime.now(UTC)

    if existing is not None:
        merged_evidence, added = _merge_json_objects(existing.evidence or [], evidence)
        existing.evidence = merged_evidence
        existing.tags = list(dict.fromkeys([*(existing.tags or []), *tags]))
        existing.confidence = max(existing.confidence, payload.confidence)
        if existing.source_uri is None and payload.source_uri:
            existing.source_uri = payload.source_uri
        if existing.source_published_at is None and payload.source_published_at:
            existing.source_published_at = payload.source_published_at
        metadata = dict(existing.metadata_json or {})
        conflicts_raw = metadata.get("ingest_conflicts", [])
        conflicts = list(conflicts_raw) if isinstance(conflicts_raw, list) else []
        if existing.epistemic_status != payload.epistemic_status.value:
            conflicts.append(
                {
                    "field": "epistemic_status",
                    "existing": existing.epistemic_status,
                    "incoming": payload.epistemic_status.value,
                    "at": now.isoformat(),
                }
            )
        metadata.update(payload.metadata_json)
        if conflicts:
            metadata["ingest_conflicts"] = conflicts[-20:]
        metadata["last_ingested_at"] = now.isoformat()
        existing.metadata_json = metadata
        return existing, False, added

    claim = KnowledgeClaim(
        namespace=payload.namespace,
        project_id=payload.project_id,
        created_by_agent_id=created_by_agent_id or payload.created_by_agent_id,
        statement=payload.statement.strip(),
        fingerprint=fingerprint,
        epistemic_status=payload.epistemic_status.value,
        lifecycle_status=KnowledgeLifecycle.raw.value,
        confidence=payload.confidence,
        source_name=payload.source_name,
        source_uri=payload.source_uri,
        source_published_at=payload.source_published_at,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        evidence=evidence,
        tags=tags,
        metadata_json={**payload.metadata_json, "last_ingested_at": now.isoformat()},
    )
    db.add(claim)
    db.flush()
    return claim, True, len(evidence)


def transition_claim(
    db: Session,
    claim: KnowledgeClaim,
    *,
    target: KnowledgeLifecycle,
    supersedes_id: UUID | None = None,
) -> KnowledgeClaim:
    current = claim.lifecycle_status
    target_value = target.value
    if current == target_value:
        return claim
    if target_value not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid knowledge transition {current} -> {target_value}")
    if supersedes_id is not None and target != KnowledgeLifecycle.canonical:
        raise ValueError("supersedes_id is only accepted when promoting to canonical")

    if supersedes_id is not None:
        previous = db.get(KnowledgeClaim, supersedes_id)
        if previous is None:
            raise LookupError("superseded knowledge claim not found")
        if previous.id == claim.id:
            raise ValueError("a knowledge claim cannot supersede itself")
        if previous.namespace != claim.namespace:
            raise ValueError("knowledge claims can only supersede claims in the same namespace")
        previous.lifecycle_status = KnowledgeLifecycle.superseded.value
        claim.supersedes_id = previous.id

    claim.lifecycle_status = target_value
    if target == KnowledgeLifecycle.canonical:
        claim.promoted_at = datetime.now(UTC)
    db.flush()
    return claim


def record_outcome(
    db: Session,
    claim: KnowledgeClaim,
    payload: KnowledgeOutcomeCreate,
    *,
    created_by_agent_id: UUID | None = None,
) -> KnowledgeOutcome:
    outcome = KnowledgeOutcome(
        claim_id=claim.id,
        project_id=payload.project_id or claim.project_id,
        created_by_agent_id=created_by_agent_id or payload.created_by_agent_id,
        verdict=payload.verdict.value,
        observed_result=payload.observed_result.strip(),
        error_metric=payload.error_metric,
        evidence=[item.model_dump(mode="json") for item in payload.evidence],
        metadata_json=payload.metadata_json,
        evaluated_at=payload.evaluated_at or datetime.now(UTC),
    )
    db.add(outcome)

    metadata = dict(claim.metadata_json or {})
    counters_raw = metadata.get("outcome_counts", {})
    counters = dict(counters_raw) if isinstance(counters_raw, dict) else {}
    counters[payload.verdict.value] = int(counters.get(payload.verdict.value, 0)) + 1
    metadata["outcome_counts"] = counters
    metadata["last_outcome"] = {
        "verdict": payload.verdict.value,
        "evaluated_at": outcome.evaluated_at.isoformat(),
        "error_metric": payload.error_metric,
    }
    claim.metadata_json = metadata
    db.flush()
    return outcome


def retrieve_context(
    db: Session,
    *,
    namespace: str,
    q: str | None = None,
    project_id: UUID | None = None,
    limit: int = 20,
) -> list[KnowledgeClaim]:
    now = datetime.now(UTC)
    statement = select(KnowledgeClaim).where(
        KnowledgeClaim.namespace == namespace,
        KnowledgeClaim.lifecycle_status.in_(
            [KnowledgeLifecycle.validated.value, KnowledgeLifecycle.canonical.value]
        ),
        or_(KnowledgeClaim.valid_from.is_(None), KnowledgeClaim.valid_from <= now),
        or_(KnowledgeClaim.valid_until.is_(None), KnowledgeClaim.valid_until >= now),
    )
    if project_id is not None:
        statement = statement.where(KnowledgeClaim.project_id == project_id)
    if q:
        statement = statement.where(KnowledgeClaim.statement.ilike(f"%{q.strip()}%"))
    statement = statement.order_by(
        KnowledgeClaim.confidence.desc(), KnowledgeClaim.updated_at.desc()
    )
    return list(db.scalars(statement.limit(min(max(limit, 1), 100))))


def render_claim_markdown(claim: KnowledgeClaim) -> str:
    tags = [str(tag) for tag in (claim.tags or [])]
    frontmatter = [
        "---",
        f'id: "{claim.id}"',
        f'namespace: "{claim.namespace}"',
        f'lifecycle: "{claim.lifecycle_status}"',
        f'epistemic_status: "{claim.epistemic_status}"',
        f"confidence: {claim.confidence}",
        f'source: {json.dumps(claim.source_name, ensure_ascii=False)}',
        f"tags: {json.dumps(tags, ensure_ascii=False)}",
    ]
    if claim.project_id:
        frontmatter.append(f'project_id: "{claim.project_id}"')
    if claim.source_uri:
        frontmatter.append(
            f"source_uri: {json.dumps(claim.source_uri, ensure_ascii=False)}"
        )
    if claim.source_published_at:
        frontmatter.append(f'source_published_at: "{claim.source_published_at.isoformat()}"')
    if claim.valid_from:
        frontmatter.append(f'valid_from: "{claim.valid_from.isoformat()}"')
    if claim.valid_until:
        frontmatter.append(f'valid_until: "{claim.valid_until.isoformat()}"')
    if claim.supersedes_id:
        frontmatter.append(f'supersedes: "{claim.supersedes_id}"')
    frontmatter.extend(["---", ""])

    evidence_lines: list[str] = []
    for item in claim.evidence or []:
        if isinstance(item, dict):
            source = item.get("source", "evidence")
            locator = item.get("locator")
            uri = item.get("uri")
            detail = " — ".join(str(part) for part in (locator, uri) if part)
            evidence_lines.append(f"- {source}" + (f": {detail}" if detail else ""))
        else:
            evidence_lines.append(f"- {item}")
    if not evidence_lines:
        evidence_lines.append("- No structured evidence locator recorded.")

    outcome_counts = (claim.metadata_json or {}).get("outcome_counts", {})
    return "\n".join(
        [
            *frontmatter,
            "# Knowledge Claim",
            "",
            "## Claim",
            "",
            claim.statement,
            "",
            "## Evidence",
            "",
            *evidence_lines,
            "",
            "## Outcome feedback",
            "",
            f"`{json.dumps(outcome_counts, ensure_ascii=False, sort_keys=True)}`",
            "",
            "## Provenance",
            "",
            f"- Source: {claim.source_name}",
            f"- Fingerprint: `{claim.fingerprint}`",
            f"- Updated: {claim.updated_at.isoformat() if claim.updated_at else 'pending'}",
            "",
        ]
    )


def _slug(value: str, *, fallback: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", normalized).strip("-._").lower()
    return (slug[:80] or fallback).strip("-._") or fallback


def export_claim_to_obsidian(claim: KnowledgeClaim) -> tuple[str, int]:
    if not settings.obsidian_vault_path:
        raise RuntimeError("OBSIDIAN_VAULT_PATH is not configured")
    if claim.lifecycle_status not in {
        KnowledgeLifecycle.validated.value,
        KnowledgeLifecycle.canonical.value,
    }:
        raise ValueError("only validated or canonical knowledge can be exported to Obsidian")

    vault = Path(settings.obsidian_vault_path).expanduser().resolve()
    root = (vault / settings.obsidian_knowledge_root).resolve()
    try:
        root.relative_to(vault)
    except ValueError as exc:
        raise RuntimeError("OBSIDIAN_KNOWLEDGE_ROOT escapes the configured vault") from exc

    namespace_dir = root / _slug(claim.namespace, fallback="shared")
    namespace_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_slug(claim.statement[:72], fallback='claim')}-{str(claim.id)[:8]}.md"
    target = (namespace_dir / filename).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("resolved Obsidian export path escaped the knowledge root") from exc

    markdown = render_claim_markdown(claim)
    temp = target.with_suffix(".md.tmp")
    temp.write_text(markdown, encoding="utf-8")
    temp.replace(target)
    relative = str(target.relative_to(vault))
    claim.obsidian_path = relative
    return relative, len(markdown.encode("utf-8"))
