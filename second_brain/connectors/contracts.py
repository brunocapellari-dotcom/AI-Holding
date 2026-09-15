from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from second_brain.schemas import EpistemicNature, InformationClass, RiskLevel


class ContentModality(StrEnum):
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    BOOK = "BOOK"
    PAPER = "PAPER"
    NEWS = "NEWS"
    WEBSITE = "WEBSITE"
    API = "API"
    RSS = "RSS"
    IMAGE = "IMAGE"
    UPLOAD = "UPLOAD"


@dataclass(frozen=True)
class AcquiredContent:
    source_id: str
    namespace: str
    modality: ContentModality
    content: bytes
    mime_type: str
    filename: str | None = None
    source_uri: str | None = None
    external_id: str | None = None
    title: str | None = None
    author_or_institution: str | None = None
    document_date: datetime | None = None
    publication_date: datetime | None = None
    reference_date: datetime | None = None
    collected_at: datetime | None = None
    information_class: InformationClass = InformationClass.INTERNAL
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ContentSegment:
    locator: str
    text: str
    kind: str = "text"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class InterpretedContent:
    title: str
    text: str
    segments: tuple[ContentSegment, ...]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposedClaim:
    statement: str
    confidence: float
    risk_level: RiskLevel = RiskLevel.LOW
    nature: EpistemicNature = EpistemicNature.STRUCTURAL
    assertion_key: str | None = None
    normalized_value: str | None = None
    unit: str | None = None
    evidence_locators: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class ContentInterpreter(Protocol):
    def interpret(self, acquired: AcquiredContent, *, data_only_context: str) -> InterpretedContent: ...


class ClaimExtractionEngine(Protocol):
    def extract(
        self,
        interpreted: InterpretedContent,
        *,
        data_only_context: str,
    ) -> tuple[ProposedClaim, ...]: ...
