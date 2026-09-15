from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from second_brain.schemas import InformationClass

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]{8,}", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
)


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    message: str


def scan_text_for_secrets(text: str) -> tuple[SecurityFinding, ...]:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return (SecurityFinding("POSSIBLE_SECRET", "possible credential or private key detected"),)
    return ()


def scan_object_for_secrets(value: Any) -> tuple[SecurityFinding, ...]:
    if isinstance(value, str):
        return scan_text_for_secrets(value)
    if isinstance(value, dict):
        findings: list[SecurityFinding] = []
        for key, item in value.items():
            findings.extend(scan_text_for_secrets(str(key)))
            findings.extend(scan_object_for_secrets(item))
        return tuple(findings)
    if isinstance(value, (list, tuple, set)):
        findings = []
        for item in value:
            findings.extend(scan_object_for_secrets(item))
        return tuple(findings)
    return ()


def allow_standard_vault_export(information_class: InformationClass) -> bool:
    return information_class in {InformationClass.PUBLIC, InformationClass.INTERNAL}


def allow_graph_projection(information_class: InformationClass) -> bool:
    return information_class in {InformationClass.PUBLIC, InformationClass.INTERNAL}
