import pytest

from services.model_gateway.router import (
    RoutingDenied,
    RoutingRequest,
    WorkloadClass,
    route_model,
)


def test_routine_defaults_to_llama_lane():
    decision = route_model(RoutingRequest(workload=WorkloadClass.routine))
    assert decision.model_alias == "llama-routine"


def test_private_work_fails_closed_without_authorized_llama_endpoint():
    with pytest.raises(RoutingDenied, match="no authorized"):
        route_model(RoutingRequest(workload=WorkloadClass.executive, private=True))


def test_private_work_prefers_local_llama_and_can_use_authorized_remote_fallback():
    local = route_model(
        RoutingRequest(
            workload=WorkloadClass.research,
            private=True,
            local_available=True,
        )
    )
    assert local.model_alias == "llama-private"

    remote = route_model(
        RoutingRequest(
            workload=WorkloadClass.research,
            private=True,
            remote_private_authorized=True,
        )
    )
    assert remote.model_alias == "llama-private-remote"


def test_coding_routes_to_specialized_coding_lane():
    decision = route_model(RoutingRequest(workload=WorkloadClass.coding))
    assert decision.model_alias == "coding-primary"


def test_audit_requires_producer_and_excludes_it():
    with pytest.raises(RoutingDenied, match="producer model identity"):
        route_model(RoutingRequest(workload=WorkloadClass.audit))

    decision = route_model(
        RoutingRequest(
            workload=WorkloadClass.audit,
            producer_model="coding-primary",
        )
    )
    assert decision.model_alias == "audit-independent"
    assert decision.excluded_model == "coding-primary"

    with pytest.raises(RoutingDenied, match="same logical model"):
        route_model(
            RoutingRequest(
                workload=WorkloadClass.audit,
                producer_model="audit-independent",
            )
        )
