import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from second_brain.compat import adapt_legacy_holding_claim
from second_brain.graph import GraphitiAdapter, GraphitiConfig, build_episode
from second_brain.lifecycle import require_transition
from second_brain.schemas import (
    Claim,
    EpistemicNature,
    Evaluation,
    Fact,
    InformationClass,
    LifecycleStatus,
    Provenance,
    RiskLevel,
    TemporalContext,
)
from second_brain.schemas.export import export_json_schemas
from second_brain.taxonomy import project_namespace, shared_namespace
from second_brain.temporal import visible_as_of
from second_brain.validation import evaluate_claim_for_canonicalization
from second_brain.vault import lint_vault, render_markdown, write_markdown_atomic


def provenance(suffix: str = "001") -> Provenance:
    return Provenance(source_id=f"sb:source:source-{suffix}", confidence=0.95)


def fact(
    suffix: str = "001",
    *,
    status: LifecycleStatus = LifecycleStatus.CANONICO,
    temporal: TemporalContext | None = None,
    information_class: InformationClass = InformationClass.INTERNAL,
) -> Fact:
    return Fact(
        id=f"sb:fact:fact-{suffix}",
        namespace="shared/macro",
        information_class=information_class,
        statement=f"Institutional fact {suffix}.",
        status=status,
        nature=EpistemicNature.OBSERVED,
        confidence=0.95,
        claim_ids=[f"sb:claim:claim-{suffix}"],
        evidence_ids=[f"sb:evidence:evidence-{suffix}"],
        validation_ids=[f"sb:evaluation:evaluation-{suffix}"],
        provenance=provenance(suffix),
        temporal=temporal or TemporalContext(),
    )


def validated_claim(risk: RiskLevel = RiskLevel.LOW) -> Claim:
    return Claim(
        id="sb:claim:claim-validation-001",
        namespace="project/agrolog",
        statement="Governed validation claim.",
        status=LifecycleStatus.VALIDADO,
        nature=EpistemicNature.STRUCTURAL,
        confidence=0.91,
        risk_level=risk,
        evidence_ids=["sb:evidence:evidence-v1", "sb:evidence:evidence-v2"],
        provenance=provenance("validation-001"),
    )


def evaluation(index: int, *, human: bool = False) -> Evaluation:
    return Evaluation(
        id=f"sb:evaluation:evaluation-review-{index}",
        namespace="project/agrolog",
        target_id="sb:claim:claim-validation-001",
        evaluator_id=f"auditor-{index}",
        verdict="APPROVE",
        independent=True,
        human_approval=human,
    )


def test_temporal_contract_rejects_reverse_window() -> None:
    with pytest.raises(ValidationError):
        TemporalContext(
            valid_from=datetime(2026, 9, 11, tzinfo=UTC),
            valid_to=datetime(2026, 9, 10, tzinfo=UTC),
        )


def test_proposed_claim_cannot_be_fact() -> None:
    with pytest.raises(ValidationError):
        fact("bad", status=LifecycleStatus.PROPOSTO)


def test_low_risk_requires_two_independent_sources() -> None:
    denied = evaluate_claim_for_canonicalization(validated_claim(), [], independent_source_count=1)
    approved = evaluate_claim_for_canonicalization(validated_claim(), [], independent_source_count=2)
    assert not denied.approved
    assert approved.approved


def test_critical_requires_independent_reviews_and_human_approval() -> None:
    claim = validated_claim(RiskLevel.CRITICAL)
    denied = evaluate_claim_for_canonicalization(
        claim, [evaluation(1), evaluation(2)], independent_source_count=4
    )
    approved = evaluate_claim_for_canonicalization(
        claim, [evaluation(1), evaluation(2, human=True)], independent_source_count=4
    )
    assert not denied.approved
    assert approved.approved


def test_canonical_lifecycle_cannot_regress() -> None:
    with pytest.raises(ValueError):
        require_transition(LifecycleStatus.CANONICO, LifecycleStatus.EM_REVISAO)


def test_superseded_fact_remains_historically_queryable() -> None:
    old = fact(
        "old-001",
        status=LifecycleStatus.SUPERADO,
        temporal=TemporalContext(
            valid_from=datetime(2026, 9, 10, tzinfo=UTC),
            valid_to=datetime(2026, 9, 11, tzinfo=UTC),
            known_from=datetime(2026, 9, 10, 12, tzinfo=UTC),
        ),
    )
    new = fact(
        "new-001",
        temporal=TemporalContext(
            valid_from=datetime(2026, 9, 11, tzinfo=UTC),
            known_from=datetime(2026, 9, 11, 12, tzinfo=UTC),
        ),
    )
    old_time = datetime(2026, 9, 10, 18, tzinfo=UTC)
    new_time = datetime(2026, 9, 11, 18, tzinfo=UTC)
    assert visible_as_of(old, valid_at=old_time, known_at=old_time)
    assert not visible_as_of(new, valid_at=old_time, known_at=old_time)
    assert not visible_as_of(old, valid_at=new_time, known_at=new_time)
    assert visible_as_of(new, valid_at=new_time, known_at=new_time)


def test_graph_projection_is_deterministic_and_non_mutating() -> None:
    record = fact("graph-001")
    before = record.model_dump(mode="json")
    assert build_episode(record) == build_episode(record)
    assert record.model_dump(mode="json") == before


def test_graphiti_is_disabled_by_default_and_has_no_vault_write_path() -> None:
    class DummyClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def add_episode(self, **kwargs: object) -> None:
            self.calls.append(kwargs)

    client = DummyClient()
    episode = build_episode(fact("adapter-001"))
    with pytest.raises(RuntimeError):
        asyncio.run(GraphitiAdapter(client).upsert(episode))
    adapter = GraphitiAdapter(client, config=GraphitiConfig(enabled=True))
    asyncio.run(adapter.upsert(episode))
    assert client.calls
    assert not hasattr(adapter, "write_vault")


def test_standard_vault_blocks_restricted_information() -> None:
    with pytest.raises(PermissionError):
        render_markdown(fact("restricted-001", information_class=InformationClass.RESTRICTED))


def test_markdown_is_plain_readable_and_linter_detects_integrity_errors(tmp_path: Path) -> None:
    record = fact("vault-001")
    rendered = render_markdown(record)
    assert rendered.startswith("---\n")
    path = write_markdown_atomic(tmp_path, record)
    assert path.read_text(encoding="utf-8") == rendered
    (tmp_path / "duplicate.md").write_text(
        rendered + "\n[[missing-note]]\n", encoding="utf-8"
    )
    codes = {item.code for item in lint_vault(tmp_path)}
    assert "DUPLICATE_ID" in codes
    assert "BROKEN_LINK" in codes


def test_legacy_adapter_namespace_and_schema_export(tmp_path: Path) -> None:
    snapshot = adapt_legacy_holding_claim(
        {
            "id": "legacy-001",
            "namespace": "project/agrolog",
            "statement": "Legacy canonical statement",
            "lifecycle_status": "canonical",
            "confidence": 95,
            "source_name": "legacy",
        }
    )
    assert snapshot.status == LifecycleStatus.CANONICO
    assert snapshot.confidence == 0.95
    assert project_namespace("AgroLogMT") == "project/agrolog"
    assert shared_namespace("macro") == "shared/macro"
    names = {path.name for path in export_json_schemas(tmp_path)}
    assert {"source.schema.json", "claim.schema.json", "fact.schema.json"} <= names
