from services.policy.tool_authorization import (
    ToolGrant,
    ToolOutcome,
    ToolRequest,
    authorize_tool_call,
)

GRANTS = (
    ToolGrant(
        agent_key="PMO_IA",
        project_key="AI_HOLDING",
        tool="github.read",
        scopes=frozenset({"read"}),
    ),
    ToolGrant(
        agent_key="PMO_IA",
        project_key="AI_HOLDING",
        tool="github.issue",
        scopes=frozenset({"read", "write"}),
    ),
)


def test_forbidden_tool_is_denied_without_explicit_grant():
    decision = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="shell.root",
            scopes=frozenset({"execute", "admin"}),
        ),
        GRANTS,
    )
    assert decision.outcome == ToolOutcome.deny
    assert decision.granted_scopes == frozenset()


def test_privilege_escalation_scope_is_denied():
    decision = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="github.read",
            scopes=frozenset({"read", "write"}),
        ),
        GRANTS,
    )
    assert decision.outcome == ToolOutcome.deny
    assert "write" in decision.reasons[0]


def test_cross_project_access_requires_a_separate_grant():
    decision = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AGROLOG_MT",
            tool="github.read",
            scopes=frozenset({"read"}),
        ),
        GRANTS,
    )
    assert decision.outcome == ToolOutcome.deny


def test_untrusted_prompt_cannot_trigger_mutating_tool_autonomously():
    decision = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="github.issue",
            scopes=frozenset({"write"}),
            source_untrusted=True,
        ),
        GRANTS,
    )
    assert decision.outcome == ToolOutcome.require_human


def test_untrusted_content_can_remain_read_only_inside_explicit_grant():
    decision = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="github.read",
            scopes=frozenset({"read"}),
            source_untrusted=True,
        ),
        GRANTS,
    )
    assert decision.outcome == ToolOutcome.allow
    assert decision.granted_scopes == frozenset({"read"})


def test_external_and_irreversible_effects_are_human_gated():
    external = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="github.issue",
            scopes=frozenset({"write"}),
            external_side_effect=True,
        ),
        GRANTS,
    )
    assert external.outcome == ToolOutcome.require_human

    irreversible = authorize_tool_call(
        ToolRequest(
            agent_key="PMO_IA",
            project_key="AI_HOLDING",
            tool="github.issue",
            scopes=frozenset({"write"}),
            irreversible=True,
        ),
        GRANTS,
    )
    assert irreversible.outcome == ToolOutcome.require_human
