from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkloadClass(StrEnum):
    routine = "routine"
    executive = "executive"
    research = "research"
    coding = "coding"
    audit = "audit"


class RoutingDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class RoutingRequest:
    workload: WorkloadClass
    private: bool = False
    local_available: bool = False
    remote_private_authorized: bool = False
    producer_model: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    model_alias: str
    reason: str
    excluded_model: str | None = None


DEFAULT_ALIASES: dict[WorkloadClass, str] = {
    WorkloadClass.routine: "llama-routine",
    WorkloadClass.executive: "executive-best",
    WorkloadClass.research: "research-premium",
    WorkloadClass.coding: "coding-primary",
    WorkloadClass.audit: "audit-independent",
}


def route_model(request: RoutingRequest) -> RoutingDecision:
    """Return a logical LiteLLM alias without exposing provider credentials.

    Privacy is fail-closed. Private work uses a Llama-compatible alias and can
    leave the local boundary only when an authorized remote-private endpoint is
    explicitly available. Audit requests carry a producer exclusion that the
    LiteLLM policy layer must enforce against concrete deployments.
    """

    if request.private:
        if request.local_available:
            return RoutingDecision(
                model_alias="llama-private",
                reason="private workload is routed to the local Llama-compatible runtime",
            )
        if request.remote_private_authorized:
            return RoutingDecision(
                model_alias="llama-private-remote",
                reason="private workload uses an explicitly authorized remote Llama endpoint",
            )
        raise RoutingDenied("private workload has no authorized Llama-compatible endpoint")

    if request.workload == WorkloadClass.audit:
        if not request.producer_model:
            raise RoutingDenied("audit routing requires the producer model identity")
        if request.producer_model == DEFAULT_ALIASES[WorkloadClass.audit]:
            raise RoutingDenied("audit model cannot be the same logical model as the producer")
        return RoutingDecision(
            model_alias=DEFAULT_ALIASES[WorkloadClass.audit],
            reason="audit must use an independent model policy",
            excluded_model=request.producer_model,
        )

    alias = DEFAULT_ALIASES[request.workload]
    reasons = {
        WorkloadClass.routine: "routine work defaults to the Llama-compatible low-cost lane",
        WorkloadClass.executive: "executive reasoning uses the best authorized reasoning alias",
        WorkloadClass.research: "research uses the premium authorized research alias",
        WorkloadClass.coding: "coding is delegated to the authorized Codex/Claude coding lane",
    }
    return RoutingDecision(model_alias=alias, reason=reasons[request.workload])
