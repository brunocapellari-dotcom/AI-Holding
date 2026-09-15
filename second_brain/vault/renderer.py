from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from second_brain.schemas import (
    Claim,
    Decision,
    Document,
    Entity,
    Evaluation,
    Event,
    Evidence,
    Fact,
    Learning,
    Method,
    Model,
    Observation,
    Relation,
    Skill,
    Source,
)
from second_brain.security import allow_standard_vault_export, scan_object_for_secrets

VaultRecord = (
    Source
    | Document
    | Observation
    | Evidence
    | Claim
    | Fact
    | Entity
    | Relation
    | Event
    | Method
    | Model
    | Skill
    | Decision
    | Evaluation
    | Learning
)

_STATIC_FOLDER_BY_TYPE = {
    "Source": "03_SOURCES",
    "Document": "12_REFERENCES/documents",
    "Evidence": "12_REFERENCES/evidence",
    "Observation": "06_EVENTS/observations",
    "Claim": "00_CORE/claims",
    "Method": "04_METHODS",
    "Model": "05_MODELS",
    "Event": "06_EVENTS",
    "Skill": "08_SKILLS",
    "Entity": "09_ENTITIES",
    "Relation": "09_ENTITIES/relations",
    "Learning": "13_LEARNINGS",
    "Decision": "14_DECISIONS",
    "Evaluation": "15_EVALUATIONS",
}


def _slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-._").lower()
    return value[:90] or "record"


def _frontmatter(record: VaultRecord) -> dict[str, Any]:
    raw = record.model_dump(mode="json")
    metadata: dict[str, Any] = {
        "id": raw["id"],
        "type": raw["record_type"],
        "namespace": raw["namespace"],
        "information_class": raw["information_class"],
        "schema_version": raw["schema_version"],
        "created_at": raw["created_at"],
        "updated_at": raw["updated_at"],
    }
    for key in (
        "status",
        "confidence",
        "risk_level",
        "nature",
        "assertion_key",
        "normalized_value",
        "unit",
        "source_id",
        "document_id",
        "primary_source_id",
        "independence_group",
        "supersedes_id",
        "subject_id",
        "object_id",
        "target_id",
        "evidence_ids",
        "claim_ids",
        "validation_ids",
        "entity_ids",
        "source_ids",
        "method_ids",
        "linked_knowledge_ids",
        "related_knowledge_ids",
        "outcome_ids",
    ):
        if key in raw and raw[key] not in (None, [], {}):
            metadata[key] = raw[key]
    temporal = raw.get("temporal")
    if temporal:
        metadata["temporal"] = temporal
    return metadata


def _section(title: str, value: Any) -> str:
    if value is None or value == [] or value == {}:
        return ""
    if isinstance(value, list):
        body = "\n".join(f"- {item}" for item in value)
    elif isinstance(value, dict):
        body = (
            "```yaml\n"
            + yaml.safe_dump(value, allow_unicode=True, sort_keys=True).strip()
            + "\n```"
        )
    else:
        body = str(value)
    return f"## {title}\n\n{body}\n"


def render_markdown(record: VaultRecord) -> str:
    if not allow_standard_vault_export(record.information_class):
        raise PermissionError("record classification is not allowed in the standard vault")
    raw = record.model_dump(mode="json")
    if scan_object_for_secrets(raw):
        raise ValueError("vault export blocked by secret scanner")

    title = (
        raw.get("canonical_name")
        or raw.get("name")
        or raw.get("title")
        or raw.get("statement")
        or raw["id"]
    )
    frontmatter = yaml.safe_dump(
        _frontmatter(record),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    parts = ["---", frontmatter, "---", "", f"# {title}", ""]
    preferred = [
        ("Statement", raw.get("statement")),
        ("Purpose", raw.get("purpose")),
        ("Description", raw.get("description")),
        ("Decision", raw.get("decision")),
        ("Rationale", raw.get("rationale")),
        ("Lesson", raw.get("lesson")),
        ("Procedure", raw.get("procedure")),
        ("Evidence", raw.get("evidence_ids")),
        ("Claims", raw.get("claim_ids")),
        ("Validations", raw.get("validation_ids")),
        ("Limitations", raw.get("limitations")),
        ("Provenance", raw.get("provenance")),
    ]
    for heading, value in preferred:
        section = _section(heading, value)
        if section:
            parts.extend([section, ""])
    parts.extend(["## Record", "", f"`{raw['id']}`", ""])
    return "\n".join(parts).rstrip() + "\n"


def default_relative_path(record: VaultRecord) -> Path:
    raw = record.model_dump(mode="json")
    folder = _folder_for(record)
    label = str(
        raw.get("canonical_name")
        or raw.get("name")
        or raw.get("title")
        or raw.get("statement")
        or record.id
    )
    stable_suffix = hashlib.sha256(record.id.encode()).hexdigest()[:10]
    return Path(folder) / f"{_slug(label)}-{stable_suffix}.md"


def write_markdown_atomic(vault: Path, record: VaultRecord) -> Path:
    target = (vault.resolve() / default_relative_path(record)).resolve()
    try:
        target.relative_to(vault.resolve())
    except ValueError as exc:
        raise RuntimeError("vault path escape detected") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(record)
    temporary = target.with_suffix(".md.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(target)
    return target


def _folder_for(record: VaultRecord) -> str:
    if record.record_type == "Fact":
        if record.namespace.startswith("project/"):
            project_name = record.namespace.split("/", 2)[1]
            return f"02_PROJECTS/{_slug(project_name)}/knowledge"
        if record.namespace.startswith("shared/"):
            domain = record.namespace.split("/", 2)[1]
            return f"01_DOMAINS/{_slug(domain)}"
        return "00_CORE/facts"
    return _STATIC_FOLDER_BY_TYPE.get(record.record_type, "00_CORE")
