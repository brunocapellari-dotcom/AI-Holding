from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolOutcome(StrEnum):
    allow = "allow"
    require_human = "require_human"
    deny = "deny"


@dataclass(frozen=True)
class ToolGrant:
    agent_key: str
    project_key: str
    tool: str
    scopes: frozenset[str]


@dataclass(frozen=True)
class ToolRequest:
    agent_key: str
    project_key: str
    tool: str
    scopes: frozenset[str]
    source_untrusted: bool = False
    external_side_effect: bool = False
    irreversible: bool = False


@dataclass(frozen=True)
class ToolDecision:
    outcome: ToolOutcome
    granted_scopes: frozenset[str]
    reasons: tuple[str, ...]


MUTATING_SCOPES = frozenset(
    {
        "write",
        "execute",
        "deploy",
        "send",
        "delete",
        "purchase",
        "credential-change",
        "admin",
    }
)


def authorize_tool_call(
    request: ToolRequest,
    grants: tuple[ToolGrant, ...],
) -> ToolDecision:
    """Authorize a tool request without allowing prompts to widen authority.

    A caller can request less than an existing grant but never more. Project
    scope is exact: cross-project access requires an explicit separate grant.
    This contract is intended to sit immediately before the MCP/tool gateway;
    credentials are intentionally outside its inputs and outputs.
    """

    matching = tuple(
        grant
        for grant in grants
        if grant.agent_key == request.agent_key
        and grant.project_key == request.project_key
        and grant.tool == request.tool
    )
    if not matching:
        return ToolDecision(
            outcome=ToolOutcome.deny,
            granted_scopes=frozenset(),
            reasons=("no explicit tool grant matches agent, project and tool",),
        )

    allowed_scopes = frozenset().union(*(grant.scopes for grant in matching))
    unauthorized = request.scopes - allowed_scopes
    if unauthorized:
        return ToolDecision(
            outcome=ToolOutcome.deny,
            granted_scopes=frozenset(),
            reasons=(
                "requested scopes exceed the explicit grant: "
                + ",".join(sorted(unauthorized)),
            ),
        )

    if request.irreversible:
        return ToolDecision(
            outcome=ToolOutcome.require_human,
            granted_scopes=request.scopes,
            reasons=("irreversible tool call is human-gated",),
        )

    if request.external_side_effect:
        return ToolDecision(
            outcome=ToolOutcome.require_human,
            granted_scopes=request.scopes,
            reasons=("external side effect is human-gated",),
        )

    if request.source_untrusted and request.scopes & MUTATING_SCOPES:
        return ToolDecision(
            outcome=ToolOutcome.require_human,
            granted_scopes=request.scopes,
            reasons=(
                "untrusted content cannot autonomously trigger a mutating tool scope",
            ),
        )

    return ToolDecision(
        outcome=ToolOutcome.allow,
        granted_scopes=request.scopes,
        reasons=("tool call is within an explicit least-privilege grant",),
    )
