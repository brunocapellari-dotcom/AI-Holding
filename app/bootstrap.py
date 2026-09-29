from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, Project, ProjectStatus
from app.models.human_identity import HumanIdentityRole, HumanRole
from app.models.routine import Routine


@dataclass(frozen=True)
class AgentSeed:
    key: str
    name: str
    role: str
    max_autonomy: int
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ProjectSeed:
    key: str
    name: str
    strategic_goal: str
    priority: int
    autonomy_level: int
    status: ProjectStatus = ProjectStatus.active
    parent_key: str | None = None
    repository: str | None = None
    repository_path: str | None = None
    business_unit: str | None = None
    previous_repositories: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutineSeed:
    key: str
    project_key: str
    assigned_agent_key: str
    title: str
    execution_kind: str
    interval_minutes: int
    priority: int


@dataclass(frozen=True)
class RuntimeIdentitySeed:
    agent_key: str
    issuer: str
    subject: str
    email: str


AGENT_SEEDS: tuple[AgentSeed, ...] = (
    AgentSeed(
        key="CEO_IA",
        name="CEO IA",
        role="Holding portfolio and execution coordinator",
        max_autonomy=5,
        capabilities=(
            "portfolio-prioritization",
            "delegation",
            "incident-escalation",
            "resource-allocation",
        ),
    ),
    AgentSeed(
        key="PMO_IA",
        name="PMO IA",
        role="Portfolio execution and dependency manager",
        max_autonomy=4,
        capabilities=(
            "task-routing",
            "dependency-management",
            "milestone-governance",
            "continuity-management",
        ),
    ),
    AgentSeed(
        key="AUDITOR_IA",
        name="Auditor IA",
        role="Independent evidence and control reviewer",
        max_autonomy=3,
        capabilities=(
            "evidence-review",
            "quality-gates",
            "risk-review",
            "postmortem-review",
            "knowledge-promotion",
        ),
    ),
    AgentSeed(
        key="KNOWLEDGE_IA",
        name="Knowledge IA",
        role="Universal knowledge ingestion and memory steward for all projects",
        max_autonomy=4,
        capabilities=(
            "knowledge-ingestion",
            "knowledge-deduplication",
            "knowledge-retrieval",
            "outcome-learning",
            "obsidian-export",
        ),
    ),
    AgentSeed(
        key="HERMES",
        name="Hermes",
        role="User-facing executive Holding assistant",
        max_autonomy=2,
        capabilities=(
            "executive-reporting",
            "decision-queue",
            "portfolio-observation",
        ),
    ),
)


PROJECT_SEEDS: tuple[ProjectSeed, ...] = (
    ProjectSeed(
        key="SECOND_BRAIN",
        name="Segundo Cérebro Universal",
        strategic_goal=(
            "Operate the shared knowledge brain for every current and future project, "
            "with provenance, evidence, lifecycle governance and outcome learning."
        ),
        priority=0,
        autonomy_level=4,
        status=ProjectStatus.incubating,
        repository="brunocapellari-dotcom/Second-Brain",
        business_unit="Shared Core",
        previous_repositories=("brunocapellari-dotcom/AI-Holding",),
    ),
    ProjectSeed(
        key="AI_HOLDING",
        name="AI Holding",
        strategic_goal=(
            "Operate the digital Holding with audited, secure and evidence-based autonomy."
        ),
        priority=0,
        autonomy_level=4,
        repository="brunocapellari-dotcom/AI-Holding",
        business_unit="Holding",
    ),
    ProjectSeed(
        key="HERMES_AI_PLATFORM",
        name="Hermes AI Platform",
        strategic_goal=(
            "Provide shared AI, model, agent, skill and tool orchestration without taking "
            "portfolio authority from the Holding."
        ),
        priority=0,
        autonomy_level=3,
        status=ProjectStatus.incubating,
        repository="brunocapellari-dotcom/Hermes-AI-Platform",
        business_unit="Shared Core",
    ),
    ProjectSeed(
        key="AGROLOG_MT",
        name="AgroLog MT",
        strategic_goal=(
            "Deliver decision-grade agribusiness and logistics intelligence from reliable data."
        ),
        priority=1,
        autonomy_level=4,
        repository="brunocapellari-dotcom/AgroLogMT",
        business_unit="AgroLog MT",
    ),
    ProjectSeed(
        key="PECUARIA",
        name="Inteligência Pecuária",
        strategic_goal="Deliver audited cattle-market intelligence as an AgroLog MT domain.",
        priority=2,
        autonomy_level=3,
        parent_key="AGROLOG_MT",
        repository="brunocapellari-dotcom/AgroLogMT",
        business_unit="AgroLog MT",
    ),
    ProjectSeed(
        key="MARITIME_INTELLIGENCE",
        name="AgroLog Maritime Intelligence",
        strategic_goal=(
            "Measure maritime flows, port pressure, ETA and logistics risk for AgroLog MT."
        ),
        priority=2,
        autonomy_level=3,
        parent_key="AGROLOG_MT",
        repository="brunocapellari-dotcom/AgroLogMT",
        business_unit="AgroLog MT",
    ),
    ProjectSeed(
        key="GEOPOLITICAL_WATCH",
        name="Geopolitical Watch",
        strategic_goal=(
            "Produce structured geopolitical signals for Holding projects "
            "without speculative claims."
        ),
        priority=2,
        autonomy_level=3,
        repository="brunocapellari-dotcom/Geopolitical-Watch",
        business_unit="Shared Intelligence",
    ),
    ProjectSeed(
        key="MERCADO_FINANCEIRO",
        name="Mercado Financeiro",
        strategic_goal=(
            "Research and validate quantitative financial edge "
            "under deterministic capital controls."
        ),
        priority=3,
        autonomy_level=1,
        repository="brunocapellari-dotcom/Mercado-Financeiro",
        business_unit="Capital Strategies",
    ),
    ProjectSeed(
        key="INTELIGENCIA_ESPORTIVA",
        name="Inteligência Esportiva Quantitativa",
        strategic_goal=(
            "Build calibrated sports intelligence with reproducible evidence and controlled risk."
        ),
        priority=3,
        autonomy_level=1,
        repository="brunocapellari-dotcom/Sports-Intelligence",
        business_unit="Quantitative Intelligence",
    ),
    ProjectSeed(
        key="WORLDWAR_MODERN",
        name="WorldWar Modern",
        strategic_goal=(
            "Build a coherent strategic simulation around one authoritative world state."
        ),
        priority=4,
        autonomy_level=2,
        repository="brunocapellari-dotcom/Game-Studio",
        repository_path="games/worldwar-modern",
        business_unit="Interactive Systems",
    ),
    ProjectSeed(
        key="PERSONAL_PERFORMANCE_HEALTH_OS",
        name="Personal Performance & Health OS",
        strategic_goal=(
            "Operate a local-first personal performance system that turns goals, "
            "training, nutrition, recovery and health context into audited adaptive "
            "plans without overriding medical authority."

        ),
        priority=3,
        autonomy_level=2,
        repository="brunocapellari-dotcom/Personal-Performance-Health-OS",
        business_unit="Personal Performance",
    ),
    ProjectSeed(
        key="RESEARCH_AI",
        name="Research AI",
        strategic_goal=(
            "Operate shared autonomous research infrastructure for source discovery, "
            "validation, acquisition and evidence delivery across the Holding."
        ),
        priority=0,
        autonomy_level=4,
        status=ProjectStatus.incubating,
        repository="brunocapellari-dotcom/Research-AI",
        business_unit="Shared Core",
    ),
    ProjectSeed(
        key="CONTENT_FACTORY",
        name="Content Factory",
        strategic_goal=(
            "Produce audited multimodal content from approved knowledge while preserving "
            "provenance, rights, continuity and quality."
        ),
        priority=3,
        autonomy_level=3,
        status=ProjectStatus.incubating,
        repository="brunocapellari-dotcom/Content-Factory",
        business_unit="Content Operations",
    ),
    ProjectSeed(
        key="WHATSAPP_AI",
        name="WhatsApp AI",
        strategic_goal=(
            "Operate secure messaging automation and freight-intelligence workflows with "
            "canonical entities, provenance and bounded integrations."
        ),
        priority=2,
        autonomy_level=3,
        status=ProjectStatus.incubating,
        repository="brunocapellari-dotcom/WHATSAPP_AI",
        business_unit="Business Automation",
    ),
    ProjectSeed(
        key="MAINTENANCE_FIELD_INTELLIGENCE",
        name="Maintenance & Field Intelligence",
        strategic_goal=(
            "Validate a low-touch field-maintenance intelligence venture before scaling investment."
        ),
        priority=4,
        autonomy_level=1,
        status=ProjectStatus.incubating,
        business_unit="Venture Factory",
    ),
)


ROUTINE_SEEDS: tuple[RoutineSeed, ...] = (
    RoutineSeed(
        key="CONTROL_PLANE_HEALTH",
        project_key="AI_HOLDING",
        assigned_agent_key="PMO_IA",
        title="Verify production Control Plane health",
        execution_kind="control_plane_health",
        interval_minutes=10,
        priority=5,
    ),
    RoutineSeed(
        key="KNOWLEDGE_GAP_SCAN",
        project_key="SECOND_BRAIN",
        assigned_agent_key="KNOWLEDGE_IA",
        title="Scan shared knowledge for freshness and evidence gaps",
        execution_kind="knowledge_gap_scan",
        interval_minutes=360,
        priority=2,
    ),
    RoutineSeed(
        key="KNOWLEDGE_OUTCOME_REVIEW",
        project_key="SECOND_BRAIN",
        assigned_agent_key="KNOWLEDGE_IA",
        title="Review matured forecasts and inferences for missing outcomes",
        execution_kind="knowledge_outcome_review",
        interval_minutes=1440,
        priority=2,
    ),
)


def _ensure_agent(db: Session, seed: AgentSeed) -> bool:
    existing = db.scalar(select(Agent).where(Agent.key == seed.key))
    if existing:
        if existing.name != seed.name or existing.role != seed.role:
            raise RuntimeError(f"agent identity drift detected for {seed.key}")
        return False

    db.add(
        Agent(
            key=seed.key,
            name=seed.name,
            role=seed.role,
            status=AgentStatus.disabled,
            max_autonomy=seed.max_autonomy,
            model_policy={"status": "unconfigured"},
            capabilities=list(seed.capabilities),
        )
    )
    db.flush()
    return True


def _ensure_project(db: Session, seed: ProjectSeed, by_key: dict[str, Project]) -> bool:
    existing = db.scalar(select(Project).where(Project.key == seed.key))
    parent = by_key.get(seed.parent_key) if seed.parent_key else None
    if seed.parent_key and not parent:
        raise RuntimeError(f"missing canonical parent {seed.parent_key} for {seed.key}")

    if existing:
        if existing.name != seed.name:
            raise RuntimeError(f"project identity drift detected for {seed.key}")
        if seed.repository and existing.repository not in {
            None,
            seed.repository,
            *seed.previous_repositories,
        }:
            raise RuntimeError(f"repository drift detected for {seed.key}")
        if seed.repository and existing.repository != seed.repository:
            existing.repository = seed.repository
        if seed.repository_path and existing.repository_path is None:
            existing.repository_path = seed.repository_path
        if (
            seed.repository_path
            and existing.repository_path not in {None, seed.repository_path}
        ):
            raise RuntimeError(f"repository path drift detected for {seed.key}")
        expected_parent_id = parent.id if parent else None
        if existing.parent_project_id != expected_parent_id:
            raise RuntimeError(f"project hierarchy drift detected for {seed.key}")
        by_key[seed.key] = existing
        return False

    project = Project(
        key=seed.key,
        name=seed.name,
        status=seed.status,
        priority=seed.priority,
        autonomy_level=seed.autonomy_level,
        parent_project_id=parent.id if parent else None,
        repository=seed.repository,
        repository_path=seed.repository_path,
        business_unit=seed.business_unit,
        strategic_goal=seed.strategic_goal,
        metadata_json={"bootstrap_source": "canonical-portfolio-v2"},
    )
    db.add(project)
    db.flush()
    by_key[seed.key] = project
    return True


def _ensure_routine(
    db: Session,
    seed: RoutineSeed,
    projects_by_key: dict[str, Project],
    agents_by_key: dict[str, Agent],
) -> bool:
    project = projects_by_key.get(seed.project_key)
    if project is None:
        raise RuntimeError(f"routine references unknown project {seed.project_key}")
    agent = agents_by_key.get(seed.assigned_agent_key)
    if agent is None:
        raise RuntimeError(f"routine references unknown agent {seed.assigned_agent_key}")

    existing = db.scalar(
        select(Routine).where(
            Routine.project_id == project.id,
            Routine.key == seed.key,
        )
    )
    if existing is not None:
        if (
            existing.execution_kind != seed.execution_kind
            or existing.interval_minutes != seed.interval_minutes
            or existing.assigned_agent_id != agent.id
        ):
            raise RuntimeError(f"routine identity drift detected for {seed.key}")
        return False

    db.add(
        Routine(
            project_id=project.id,
            key=seed.key,
            title=seed.title,
            execution_kind=seed.execution_kind,
            interval_minutes=seed.interval_minutes,
            priority=seed.priority,
            assigned_agent_id=agent.id,
            enabled=True,
            next_due_at=datetime.now(UTC),
            metadata_json={"bootstrap_source": "canonical-routines-v1"},
        )
    )
    db.flush()
    return True


def _ensure_runtime_identity(
    db: Session,
    seed: RuntimeIdentitySeed,
    agents_by_key: dict[str, Agent],
) -> bool:
    agent = agents_by_key.get(seed.agent_key)
    if agent is None:
        raise RuntimeError(f"runtime identity references unknown agent {seed.agent_key}")

    existing = db.scalar(select(AgentIdentity).where(AgentIdentity.agent_id == agent.id))
    if existing is not None:
        if (
            existing.issuer != seed.issuer
            or existing.subject != seed.subject
            or existing.email != seed.email
        ):
            raise RuntimeError(f"runtime identity drift detected for {seed.agent_key}")
        return False

    principal_owner = db.scalar(
        select(AgentIdentity).where(
            AgentIdentity.issuer == seed.issuer,
            AgentIdentity.subject == seed.subject,
        )
    )
    if principal_owner is not None:
        raise RuntimeError(f"runtime principal already belongs to another agent: {seed.agent_key}")

    db.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer=seed.issuer,
            subject=seed.subject,
            email=seed.email,
        )
    )
    db.flush()
    return True


def _optional_identity_seed(prefix: str, agent_key: str) -> RuntimeIdentitySeed | None:
    values = {
        "issuer": os.getenv(f"{prefix}_IDENTITY_ISSUER"),
        "subject": os.getenv(f"{prefix}_IDENTITY_SUBJECT"),
        "email": os.getenv(f"{prefix}_IDENTITY_EMAIL"),
    }
    configured = [value for value in values.values() if value]
    if not configured:
        return None
    if len(configured) != len(values):
        raise RuntimeError(f"{prefix} runtime identity configuration must be complete")
    return RuntimeIdentitySeed(
        agent_key=agent_key,
        issuer=values["issuer"] or "",
        subject=values["subject"] or "",
        email=values["email"] or "",
    )


def _runtime_identity_seeds_from_env() -> tuple[RuntimeIdentitySeed, ...]:
    seeds = (
        _optional_identity_seed("PMO", "PMO_IA"),
        _optional_identity_seed("KNOWLEDGE", "KNOWLEDGE_IA"),
        _optional_identity_seed("AUDITOR", "AUDITOR_IA"),
    )
    return tuple(seed for seed in seeds if seed is not None)


def bootstrap_canonical_portfolio(
    db: Session,
    *,
    runtime_identities: tuple[RuntimeIdentitySeed, ...] = (),
) -> dict[str, int]:
    created_agents = sum(_ensure_agent(db, seed) for seed in AGENT_SEEDS)
    agent_keys = [seed.key for seed in AGENT_SEEDS]
    agents = db.scalars(select(Agent).where(Agent.key.in_(agent_keys)))
    agents_by_key = {agent.key: agent for agent in agents}

    projects_by_key: dict[str, Project] = {}
    created_projects = 0
    for seed in PROJECT_SEEDS:
        created_projects += int(_ensure_project(db, seed, projects_by_key))

    created_routines = sum(
        _ensure_routine(db, seed, projects_by_key, agents_by_key) for seed in ROUTINE_SEEDS
    )
    created_identities = sum(
        _ensure_runtime_identity(db, seed, agents_by_key) for seed in runtime_identities
    )
    db.commit()
    return {
        "created_agents": created_agents,
        "created_projects": created_projects,
        "created_routines": created_routines,
        "created_identities": created_identities,
        "canonical_agents": len(AGENT_SEEDS),
        "canonical_projects": len(PROJECT_SEEDS),
        "canonical_routines": len(ROUTINE_SEEDS),
        "canonical_identities": len(runtime_identities),
    }




def _owner_identity_from_env() -> tuple[str, str, str] | None:
    values = {
        "issuer": os.getenv("OWNER_IDENTITY_ISSUER"),
        "subject": os.getenv("OWNER_IDENTITY_SUBJECT"),
        "email": os.getenv("OWNER_IDENTITY_EMAIL"),
    }
    configured = [value for value in values.values() if value]
    if not configured:
        return None
    if len(configured) != len(values):
        raise RuntimeError("OWNER runtime identity configuration must be complete")
    return (
        (values["issuer"] or "").strip(),
        (values["subject"] or "").strip(),
        (values["email"] or "").strip(),
    )


def bootstrap_owner_identity(db: Session) -> bool:
    identity = _owner_identity_from_env()
    if identity is None:
        return False

    issuer, subject, email = identity
    if not issuer or not subject or not email:
        raise RuntimeError("OWNER runtime identity configuration cannot contain blank values")

    existing = db.scalar(
        select(HumanIdentityRole).where(
            HumanIdentityRole.issuer == issuer,
            HumanIdentityRole.subject == subject,
        )
    )
    if existing is not None:
        if existing.email.casefold() != email.casefold() or existing.role != HumanRole.owner.value:
            raise RuntimeError("owner identity drift detected")
        return False

    email_owner = db.scalar(
        select(HumanIdentityRole).where(HumanIdentityRole.email == email)
    )
    if email_owner is not None:
        raise RuntimeError("owner email is already bound to another verified subject")

    db.add(
        HumanIdentityRole(
            issuer=issuer,
            subject=subject,
            email=email,
            role=HumanRole.owner.value,
        )
    )
    db.flush()
    return True


def main() -> None:
    runtime_identities = _runtime_identity_seeds_from_env()
    with SessionLocal() as db:
        result = bootstrap_canonical_portfolio(
            db,
            runtime_identities=runtime_identities,
        )
        owner_created = bootstrap_owner_identity(db)
        db.commit()
    result["owner_identity_created"] = int(owner_created)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
