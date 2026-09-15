import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.knowledge import KnowledgeLifecycle
from app.schemas.knowledge import KnowledgeTransition

ROOT = Path(__file__).resolve().parents[1]


def test_agentos_is_the_only_general_agent_runtime_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = [item.lower() for item in project["dependencies"]]
    joined = "\n".join(dependencies)

    assert "agno[" in joined
    forbidden = (
        "langgraph",
        "crewai",
        "autogen",
        "google-adk",
        "google_adk",
        "microsoft-agent-framework",
    )
    for package in forbidden:
        assert package not in joined


def test_second_brain_default_is_an_external_validation_inbox() -> None:
    settings = Settings(_env_file=None)
    assert settings.obsidian_knowledge_root.endswith("00 - Inbox/Holding")


def test_holding_cannot_canonicalize_knowledge() -> None:
    with pytest.raises(ValidationError, match="external Second Brain"):
        KnowledgeTransition(lifecycle_status=KnowledgeLifecycle.canonical)


def test_target_repository_boundaries_exist() -> None:
    required = (
        "apps/hermes",
        "apps/control_plane",
        "services/agent_runtime",
        "services/model_gateway",
        "services/coding_agents",
        "services/observability",
        "services/policy",
        "services/secrets",
        "agents",
        "workflows",
        "skills",
        "integrations/second_brain",
        "security",
        "infrastructure",
        "projects",
        "docs/architecture",
    )
    for relative in required:
        assert (ROOT / relative).is_dir(), relative
