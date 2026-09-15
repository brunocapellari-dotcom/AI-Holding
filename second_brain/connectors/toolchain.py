from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolDisposition(StrEnum):
    PRIMARY = "PRIMARY"
    FALLBACK = "FALLBACK"
    SPECIALIZED = "SPECIALIZED"
    CONDITIONAL = "CONDITIONAL"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    repository: str
    role: str
    disposition: ToolDisposition
    rationale: str
    security_note: str | None = None


FINAL_TOOLCHAIN: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="Graphiti",
        repository="getzep/graphiti",
        role="temporal_graph",
        disposition=ToolDisposition.PRIMARY,
        rationale=(
            "Temporal graph, episode provenance, bitemporal facts and hybrid retrieval; "
            "derived projection only, never canonical storage."
        ),
    ),
    ToolSpec(
        name="Docling",
        repository="docling-project/docling",
        role="document_understanding",
        disposition=ToolDisposition.PRIMARY,
        rationale=(
            "Primary multimodal document parser for PDF, Office, HTML, EPUB, images, audio "
            "and supported video/keyframe workflows."
        ),
        security_note="Run only after quarantine/MIME/hash/antivirus gates.",
    ),
    ToolSpec(
        name="MarkItDown",
        repository="microsoft/markitdown",
        role="document_understanding",
        disposition=ToolDisposition.FALLBACK,
        rationale="Lightweight fallback for simple file-to-Markdown conversion.",
        security_note="Use narrow local/stream conversion APIs; untrusted paths/URLs are gated upstream.",
    ),
    ToolSpec(
        name="Marker",
        repository="datalab-to/marker",
        role="document_understanding",
        disposition=ToolDisposition.CONDITIONAL,
        rationale="Use only when benchmarked PDF fidelity materially exceeds Docling for a source class.",
    ),
    ToolSpec(
        name="GROBID",
        repository="grobidOrg/grobid",
        role="scientific_metadata",
        disposition=ToolDisposition.SPECIALIZED,
        rationale="Scientific PDF structure, bibliographic metadata and references.",
    ),
    ToolSpec(
        name="PaperQA2",
        repository="Future-House/paper-qa",
        role="scientific_research",
        disposition=ToolDisposition.SPECIALIZED,
        rationale="Grounded scientific retrieval, evidence ranking and contradiction-oriented research.",
    ),
    ToolSpec(
        name="PyAlex",
        repository="J535D165/pyalex",
        role="scientific_discovery",
        disposition=ToolDisposition.PRIMARY,
        rationale="OpenAlex discovery/metadata client; OpenAlex IDs remain external identifiers, not Fact IDs.",
    ),
    ToolSpec(
        name="Trafilatura",
        repository="adbar/trafilatura",
        role="web_extraction",
        disposition=ToolDisposition.PRIMARY,
        rationale="Primary article/main-text extraction for HTML/web sources.",
    ),
    ToolSpec(
        name="newspaper4k",
        repository="AndyTheFactory/newspaper4k",
        role="web_extraction",
        disposition=ToolDisposition.FALLBACK,
        rationale="Fallback article extractor when the primary extractor fails quality gates.",
    ),
    ToolSpec(
        name="RSSHub",
        repository="RSSHub/RSSHub",
        role="feed_acquisition",
        disposition=ToolDisposition.SPECIALIZED,
        rationale="Feed adapter layer for sources without usable native RSS/API feeds.",
    ),
    ToolSpec(
        name="yt-dlp",
        repository="yt-dlp/yt-dlp",
        role="video_acquisition",
        disposition=ToolDisposition.PRIMARY,
        rationale="Metadata/caption/media acquisition only for authorized and policy-compliant sources.",
    ),
    ToolSpec(
        name="faster-whisper",
        repository="SYSTRAN/faster-whisper",
        role="speech_to_text",
        disposition=ToolDisposition.PRIMARY,
        rationale="Primary local transcription engine when reliable platform captions are unavailable.",
    ),
    ToolSpec(
        name="WhisperX",
        repository="m-bain/whisperX",
        role="speech_to_text",
        disposition=ToolDisposition.SPECIALIZED,
        rationale="Alignment/diarization only when the task requires speaker/timestamp precision.",
    ),
    ToolSpec(
        name="PySceneDetect",
        repository="Breakthrough/PySceneDetect",
        role="video_scene_segmentation",
        disposition=ToolDisposition.PRIMARY,
        rationale="Scene boundaries drive representative-frame selection before vision interpretation.",
    ),
    ToolSpec(
        name="ClamAV",
        repository="Cisco-Talos/clamav",
        role="malware_scanning",
        disposition=ToolDisposition.PRIMARY,
        rationale="Antivirus gate for untrusted uploaded/downloaded files where file scanning is required.",
    ),
    ToolSpec(
        name="pgvector",
        repository="pgvector/pgvector",
        role="institutional_semantic_index",
        disposition=ToolDisposition.DEFERRED,
        rationale=(
            "Add only if retrieval evaluation proves structured/lexical/Graphiti hybrid retrieval is "
            "insufficient; avoid a second vector layer without measured benefit."
        ),
    ),
)


def tools_for_role(role: str) -> tuple[ToolSpec, ...]:
    return tuple(item for item in FINAL_TOOLCHAIN if item.role == role)
