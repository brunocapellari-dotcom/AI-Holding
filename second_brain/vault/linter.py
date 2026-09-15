from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
VALID_NAMESPACES = re.compile(
    r"^(shared(?:/[a-z0-9._-]+)*|project/[a-z0-9][a-z0-9._-]{1,79}(?:/[a-z0-9._-]+)*)$"
)
_SINGLE_REFERENCE_KEYS = (
    "source_id",
    "document_id",
    "subject_id",
    "object_id",
    "supersedes_id",
    "target_id",
)
_LIST_REFERENCE_KEYS = (
    "evidence_ids",
    "claim_ids",
    "validation_ids",
    "entity_ids",
    "source_ids",
    "method_ids",
    "linked_knowledge_ids",
    "related_knowledge_ids",
    "outcome_ids",
)
_ORPHAN_CHECK_TYPES = {
    "Claim",
    "Fact",
    "Evidence",
    "Entity",
    "Relation",
    "Event",
    "Method",
    "Model",
    "Skill",
    "Learning",
}


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


def _parse_dt(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _bad_window(meta: dict[str, Any]) -> bool:
    temporal = meta.get("temporal")
    if not isinstance(temporal, dict):
        return False
    for start_key, end_key in (("valid_from", "valid_to"), ("known_from", "known_to")):
        start = temporal.get(start_key)
        end = temporal.get(end_key)
        if start and end:
            start_dt = _parse_dt(start)
            end_dt = _parse_dt(end)
            if start_dt is None or end_dt is None or end_dt < start_dt:
                return True
    publication = _parse_dt(temporal.get("publication_date"))
    collected = _parse_dt(temporal.get("collected_at"))
    if publication and collected and collected < publication:
        return True
    known_from = _parse_dt(temporal.get("known_from"))
    if collected and known_from and known_from < collected:
        return True
    return False


def _record_references(meta: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    for key in _SINGLE_REFERENCE_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value.startswith("sb:"):
            references.add(value)
    for key in _LIST_REFERENCE_KEYS:
        values = meta.get(key)
        if isinstance(values, list):
            references.update(
                str(value)
                for value in values
                if isinstance(value, str) and value.startswith("sb:")
            )
    return references


def _semantic_key(meta: dict[str, Any], text: str) -> str | None:
    if str(meta.get("type")) not in {"Claim", "Fact"}:
        return None
    match = re.search(r"^## Statement\s*\n+(.+?)(?:\n## |\Z)", text, re.M | re.S)
    if not match:
        return None
    normalized = re.sub(r"\s+", " ", match.group(1)).strip().casefold()
    normalized = re.sub(r"[^\w\s.%/-]", "", normalized)
    return normalized or None


def lint_vault(vault: Path) -> list[LintFinding]:
    notes = sorted(vault.rglob("*.md"))
    findings: list[LintFinding] = []
    records: dict[Path, dict[str, Any]] = {}
    stems = {path.stem for path in notes}
    ids: list[str] = []
    inbound: Counter[str] = Counter()
    semantic_records: defaultdict[str, list[str]] = defaultdict(list)

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
            findings.append(
                LintFinding(rel, "TEMPORAL_INCONSISTENCY", "invalid temporal chronology")
            )
        if (
            meta.get("type") == "Claim"
            and not meta.get("evidence_ids")
            and "## Evidence" not in text
        ):
            findings.append(LintFinding(rel, "CLAIM_WITHOUT_EVIDENCE", "claim has no evidence"))
        if meta.get("type") == "Evidence" and not meta.get("source_id"):
            findings.append(LintFinding(rel, "SOURCE_MISSING", "evidence has no source_id"))
        if meta.get("type") == "Fact" and str(meta.get("status")) == "CANÔNICO":
            if not meta.get("validation_ids") and "## Validations" not in text:
                findings.append(
                    LintFinding(
                        rel,
                        "CANONICAL_WITHOUT_VALIDATION",
                        "canonical fact has no validation",
                    )
                )
            if not meta.get("evidence_ids") and "## Evidence" not in text:
                findings.append(
                    LintFinding(
                        rel,
                        "CANONICAL_WITHOUT_EVIDENCE",
                        "canonical fact has no evidence",
                    )
                )
        references = _record_references(meta)
        inbound.update(references)
        semantic = _semantic_key(meta, text)
        if semantic:
            semantic_records[semantic].append(rel)

        for link in WIKILINK.findall(text):
            link_stem = Path(link.strip()).stem
            if link_stem and link_stem not in stems:
                findings.append(LintFinding(rel, "BROKEN_LINK", f"missing [[{link}]]"))
        for target in MARKDOWN_LINK.findall(text):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            if target and not target_path.exists():
                findings.append(
                    LintFinding(rel, "BROKEN_LINK", f"missing markdown link {target}")
                )

    duplicated = {record_id for record_id, count in Counter(ids).items() if count > 1}
    for path, meta in records.items():
        rel = str(path.relative_to(vault))
        record_id = str(meta.get("id", ""))
        if record_id in duplicated:
            findings.append(LintFinding(rel, "DUPLICATE_ID", record_id))

    known_ids = set(ids)
    for path, meta in records.items():
        rel = str(path.relative_to(vault))
        for reference in sorted(_record_references(meta)):
            if reference not in known_ids:
                findings.append(LintFinding(rel, "MISSING_REFERENCE", reference))
        record_id = str(meta.get("id", ""))
        if (
            record_id
            and str(meta.get("type")) in _ORPHAN_CHECK_TYPES
            and inbound[record_id] == 0
            and not bool(meta.get("allow_orphan"))
        ):
            findings.append(
                LintFinding(
                    rel,
                    "ORPHAN_NOTE",
                    "note has no inbound structured reference; set allow_orphan: true when intentional",
                )
            )

    for normalized, paths in semantic_records.items():
        if len(paths) < 2:
            continue
        summary = normalized[:120]
        for rel in paths:
            findings.append(
                LintFinding(
                    rel,
                    "DUPLICATE_STATEMENT",
                    f"same normalized claim/fact text appears in {len(paths)} notes: {summary}",
                )
            )

    supersedes: dict[str, str] = {}
    for meta in records.values():
        record_id = meta.get("id")
        supersedes_id = meta.get("supersedes_id")
        if isinstance(record_id, str) and isinstance(supersedes_id, str):
            supersedes[record_id] = supersedes_id
    for start in supersedes:
        cursor = start
        visited: set[str] = set()
        while cursor in supersedes:
            if cursor in visited:
                path = next(
                    (
                        str(candidate.relative_to(vault))
                        for candidate, meta in records.items()
                        if meta.get("id") == start
                    ),
                    "<unknown>",
                )
                findings.append(
                    LintFinding(path, "SUPERSESSION_CYCLE", f"cycle detected from {start}")
                )
                break
            visited.add(cursor)
            cursor = supersedes[cursor]

    return findings
