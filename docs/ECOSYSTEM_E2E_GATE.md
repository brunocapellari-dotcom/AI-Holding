# Ecosystem E2E Promotion Gate

The Holding is the authority that promotes a project or shared service to an operational state.

Hermes owns the transport-neutral health/evidence contract in
`Hermes-AI-Platform/contracts/ecosystem_e2e.py`.

## Mandatory evidence

A service cannot be promoted unless the same release candidate has passing evidence for:

1. CI quality gate.
2. Liveness/health.
3. Readiness, including required dependencies.
4. End-to-end execution through its real boundary.

Where applicable, the Holding must additionally require security, restore and freshness evidence.

## Core dependency order

`AI-Holding -> Hermes AI -> Research AI -> Knowledge Factory / Second Brain -> consuming project`

The consuming project must not bypass Hermes for governed AI orchestration and must not write canonical
knowledge directly to the Second Brain without the Knowledge Factory promotion policy.

## First production consumer

AgroLog MT is the first full production consumer. Its promotion requires an E2E path that records
request ID, run ID, evidence references, source provenance and final acceptance result.

## State rule

Documentation, merged code, or a green unit test suite alone is not sufficient for `OPERATIONAL`.
Missing mandatory evidence results in `PARTIAL`, `GATED`, `BLOCKED` or `UNKNOWN`.
