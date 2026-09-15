from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit

from app.models.knowledge import DataClassification


@dataclass(frozen=True)
class SecurityInspection:
    classification: DataClassification
    flags: tuple[str, ...]
    blocked: bool


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "credential_assignment",
        re.compile(
            r"\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*[^\s,;]{6,}",
            re.IGNORECASE,
        ),
    ),
)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cpf_like", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2}\b")),
    ("credit_card_like", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
)

_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "key",
    "password",
    "secret",
    "signature",
    "sig",
    "token",
    "x-amz-credential",
    "x-amz-signature",
}


def _flatten(value: object, *, limit: int = 100_000) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        rendered = str(value)
    return rendered[:limit]


def inspect_information(*values: object) -> SecurityInspection:
    text = "\n".join(_flatten(value) for value in values if value is not None)
    flags: list[str] = []
    blocked = False

    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            flags.append(name)
            blocked = True

    for name, pattern in _PII_PATTERNS:
        if pattern.search(text):
            flags.append(name)

    if blocked:
        classification = DataClassification.restricted
    elif flags:
        classification = DataClassification.confidential
    else:
        classification = DataClassification.internal

    return SecurityInspection(
        classification=classification,
        flags=tuple(dict.fromkeys(flags)),
        blocked=blocked,
    )


def validate_public_source_uri(uri: str | None) -> None:
    if uri is None:
        return
    parsed = urlsplit(uri)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("source URI must use http or https")
    if not parsed.hostname:
        raise ValueError("source URI must contain a hostname")
    if parsed.username or parsed.password:
        raise ValueError("source URI must not contain embedded credentials")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            raise ValueError("source URI contains a sensitive query parameter")


def enforce_safe_knowledge(*values: object, source_uri: str | None = None) -> SecurityInspection:
    validate_public_source_uri(source_uri)
    inspection = inspect_information(*values, source_uri)
    if inspection.blocked:
        raise ValueError(
            "knowledge payload appears to contain credentials or secret material and was rejected"
        )
    return inspection
