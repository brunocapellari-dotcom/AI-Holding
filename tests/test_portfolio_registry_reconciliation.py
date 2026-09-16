import pytest
from sqlalchemy import select

from app.bootstrap import bootstrap_canonical_portfolio
from app.models.entities import Project, ProjectStatus


def test_verified_repository_locations_are_canonical(db_session) -> None:
    bootstrap_canonical_portfolio(db_session)
    projects = {item.key: item for item in db_session.scalars(select(Project))}

    assert projects["AI_HOLDING"].repository == "brunocapellari-dotcom/AI-Holding"
    assert projects["SECOND_BRAIN"].repository == "brunocapellari-dotcom/Second-Brain"
    assert projects["HERMES_AI_PLATFORM"].repository == (
        "brunocapellari-dotcom/Hermes-AI-Platform"
    )
    assert projects["INTELIGENCIA_ESPORTIVA"].repository == (
        "brunocapellari-dotcom/Sports-Intelligence"
    )
    assert projects["WORLDWAR_MODERN"].repository == "brunocapellari-dotcom/Game-Studio"
    assert projects["WORLDWAR_MODERN"].repository_path == "games/worldwar-modern"
    assert projects["PERSONAL_PERFORMANCE_HEALTH_OS"].repository == (
        "brunocapellari-dotcom/Personal-Performance-Health-OS"
    )
    assert projects["HERMES_AI_PLATFORM"].status == ProjectStatus.incubating


def test_second_brain_known_transition_repository_is_reconciled(db_session) -> None:
    bootstrap_canonical_portfolio(db_session)
    second_brain = db_session.scalar(select(Project).where(Project.key == "SECOND_BRAIN"))
    assert second_brain is not None

    second_brain.repository = "brunocapellari-dotcom/AI-Holding"
    db_session.commit()

    result = bootstrap_canonical_portfolio(db_session)
    assert result["created_projects"] == 0
    assert second_brain.repository == "brunocapellari-dotcom/Second-Brain"


def test_unknown_repository_drift_still_fails_closed(db_session) -> None:
    bootstrap_canonical_portfolio(db_session)
    sports = db_session.scalar(select(Project).where(Project.key == "INTELIGENCIA_ESPORTIVA"))
    assert sports is not None

    sports.repository = "unexpected/repository"
    db_session.commit()

    with pytest.raises(
        RuntimeError,
        match="repository drift detected for INTELIGENCIA_ESPORTIVA",
    ):
        bootstrap_canonical_portfolio(db_session)
