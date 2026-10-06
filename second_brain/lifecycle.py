from __future__ import annotations

from dataclasses import dataclass

from second_brain.schemas import LifecycleStatus

ALLOWED_TRANSITIONS: dict[LifecycleStatus, frozenset[LifecycleStatus]] = {
    LifecycleStatus.PROPOSTO: frozenset({LifecycleStatus.EM_REVISAO, LifecycleStatus.BAIXA_CONFIANCA, LifecycleStatus.CONFLITANTE, LifecycleStatus.REJEITADO}),
    LifecycleStatus.EM_REVISAO: frozenset({LifecycleStatus.VALIDADO, LifecycleStatus.BAIXA_CONFIANCA, LifecycleStatus.CONFLITANTE, LifecycleStatus.REJEITADO}),
    LifecycleStatus.BAIXA_CONFIANCA: frozenset({LifecycleStatus.EM_REVISAO, LifecycleStatus.REJEITADO}),
    LifecycleStatus.CONFLITANTE: frozenset({LifecycleStatus.EM_REVISAO, LifecycleStatus.REJEITADO}),
    LifecycleStatus.VALIDADO: frozenset({LifecycleStatus.CANONICO, LifecycleStatus.CONFLITANTE, LifecycleStatus.REJEITADO}),
    LifecycleStatus.CANONICO: frozenset({LifecycleStatus.SUPERADO}),
    LifecycleStatus.SUPERADO: frozenset(),
    LifecycleStatus.REJEITADO: frozenset(),
}


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    reason: str


def check_transition(current: LifecycleStatus, target: LifecycleStatus) -> TransitionDecision:
    if current == target:
        return TransitionDecision(True, "idempotent transition")
    if target in ALLOWED_TRANSITIONS[current]:
        return TransitionDecision(True, "transition allowed")
    return TransitionDecision(False, f"transition {current.value} -> {target.value} is not allowed")


def require_transition(current: LifecycleStatus, target: LifecycleStatus) -> None:
    decision = check_transition(current, target)
    if not decision.allowed:
        raise ValueError(decision.reason)


LEGACY_LIFECYCLE_MAP: dict[str, LifecycleStatus] = {
    "raw": LifecycleStatus.PROPOSTO,
    "candidate": LifecycleStatus.EM_REVISAO,
    "validated": LifecycleStatus.VALIDADO,
    "canonical": LifecycleStatus.CANONICO,
    "superseded": LifecycleStatus.SUPERADO,
}
