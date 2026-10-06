from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
VALID_NAMESPACES = re.compile(
    r"^(shared(?:/[a-z0-9._-]+)*|project/[a-z0-9][a-z0-9._-]{1,79}(?:/[a-z0-9._-]+)*)$"
)


@dataclass(frozen=True)
class LintFinding:
    path: str
    code: str
    message: str


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    loaded = yaml.safe_load(text[4:end]) or {}
    return loaded if isinstance(loaded, dict) else {}


def _bad_window(meta: dict[str, Any]) -> bool:
    temporal = meta.get("temporal")
    if not isinstance(temporal, dict):
        return False
    for start_key, end_key in (("valid_from", "valid_to"), ("known_from", "known_to")):
        start = temporal.get(start_key)
        end = temporal.get(end_key)
        if start and end:
            try:
                if datetime.fromisoformat(str(end)) < datetime.fromisoformat(str(start)):
                    return True
            except ValueError:
                return True
    return False


def lint_vault(vault: Path) -> list[LintFinding]:
    notes = sorted(vault.rglob("*.md"))
    findings: list[LintFinding] = []
    records: dict[Path, dict[str, Any]] = {}
    stems = {path.stem for path in notes}
    ids: list[str] = []

    for path in notes:
        rel = str(path.relative_to(vault))
        text = path.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        records[path] = meta
        if not meta:
            findings.append(
                LintFinding(rel, "MISSING_METADATA", "YAML frontmatter is missing or invalid")
            )
            continue
        for key in ("id", "type", "namespace", "schema_version"):
            if not meta.get(key):
                findings.append(LintFinding(rel, "MISSING_METADATA", f"missing {key}"))
        if meta.get("id"):
            ids.append(str(meta["id"]))
        namespace = str(meta.get("namespace", ""))
        if namespace and not VALID_NAMESPACES.fullmatch(namespace):
            findings.append(LintFinding(rel, "INVALID_NAMESPACE", namespace))
        if _bad_window(meta):
            findings.append(LintFinding(rel, "TEMPORAL_INCONSISTENCY", "invalid temporal interval"))
        if meta.get("type") == "Claim" and not meta.get("evidence_ids") and "## Evidence" not in text:
            findings.append(LintFinding(rel, "CLAIM_WITHOUT_EVIDENCE", "claim has no evidence"))
        if meta.get("type") == "Fact" and str(meta.get("status")) == "CANÔNICO":
            if not meta.get("validation_ids") and "## Validations" not in text:
                findings.append(
                    LintFinding(rel, "CANONICAL_WITHOUT_VALIDATION", "canonical fact has no validation")
                )
        for link in WIKILINK.findall(text):
            link_stem = Path(link.strip()).stem
            if link_stem and link_stem not in stems:
                findings.append(LintFinding(rel, "BROKEN_LINK", f"missing [[{link}]]"))

    duplicated = {record_id for record_id, count in Counter(ids).items() if count > 1}
    for path, meta in records.items():
        record_id = str(meta.get("id", ""))
        if record_id in duplicated:
            findings.append(LintFinding(str(path.relative_to(vault)), "DUPLICATE_ID", record_id))

    known_ids = set(ids)
    for path, meta in records.items():
        rel = str(path.relative_to(vault))
        for key in ("source_id", "subject_id", "object_id"):
            value = meta.get(key)
            if isinstance(value, str) and value.startswith("sb:") and value not in known_ids:
                findings.append(LintFinding(rel, "MISSING_REFERENCE", f"{key}={value}"))
    return findings
