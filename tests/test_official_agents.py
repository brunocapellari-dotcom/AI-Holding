from sqlalchemy import select

from app.bootstrap import AGENT_SEEDS, bootstrap_canonical_portfolio
from app.models.entities import Agent, AgentStatus

OFFICIAL_AGENT_KEYS = {
    "HERMES",
    "CEO_IA",
    "PMO_IA",
    "GOVERNANCE_IA",
    "RISK_IA",
    "AUDITOR_IA",
    "SECURITY_IA",
    "ARCHITECT_IA",
    "FINANCE_IA",
}


def test_official_holding_agents_are_canonical_seeds():
    seed_keys = {seed.key for seed in AGENT_SEEDS}
    assert OFFICIAL_AGENT_KEYS <= seed_keys


def test_new_official_agents_are_fail_closed_until_runtime_is_provisioned(db_session):
    bootstrap_canonical_portfolio(db_session)
    agents = {
        agent.key: agent
        for agent in db_session.scalars(select(Agent).where(Agent.key.in_(OFFICIAL_AGENT_KEYS)))
    }
    assert set(agents) == OFFICIAL_AGENT_KEYS
    assert all(agent.status == AgentStatus.disabled for agent in agents.values())
    assert all(agent.model_policy == {"status": "unconfigured"} for agent in agents.values())
