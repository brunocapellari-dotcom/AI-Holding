# Universal Knowledge Core

The Universal Knowledge Core is the shared memory and learning layer for every project. It is not owned by the AI Holding domain; the Holding is one consumer of the same brain used by AgroLog MT, Mercado Financeiro, Inteligência Esportiva, Geopolitical Watch and future projects.

## Operating model

Each project can publish structured claims into a namespace. A claim stores the statement, source, evidence locators, epistemic status, confidence, validity window, project provenance and creating agent. The lifecycle is deliberately gated:

`raw -> candidate -> validated -> canonical -> superseded`

Knowledge IA can ingest, merge evidence, record outcomes and export approved knowledge to Obsidian. Auditor IA owns promotion. This separation prevents an ingesting agent from promoting its own conclusion directly to canonical truth.

## Epistemic status

Claims are classified as one of:

- `observed`: directly observed from a source or measurement.
- `estimated`: estimated from observed inputs.
- `projected`: forward-looking projection.
- `inferred`: analytical inference from evidence.
- `structural`: durable methodology, definition or domain knowledge.

Lifecycle and epistemic status are separate dimensions. A projected claim may become canonical as the canonical record of a forecast, without being misrepresented as an observation.

## Deduplication and contradiction handling

Ingestion normalizes whitespace and case, computes a SHA-256 fingerprint and deduplicates within each namespace. Re-ingestion merges new evidence and tags instead of creating another copy. A conflicting incoming epistemic classification is recorded in metadata for audit rather than silently replacing the stored classification.

A canonical claim may supersede another claim in the same namespace. The prior claim remains stored as `superseded`, preserving history.

## Outcome learning

Claims can receive outcome records with verdicts:

- `confirmed`
- `partially_confirmed`
- `refuted`
- `inconclusive`

An outcome stores the observed result, optional numeric error metric and evidence. Outcome counters are attached to claim metadata. This creates the first closed feedback loop needed for later calibration, post-mortems and agent autonomy scoring. Outcome recording does not automatically rewrite confidence or promote/demote knowledge; those policies remain auditable and deterministic.

## Retrieval contract

Agents should query `GET /api/v1/knowledge/context` before material work. This endpoint only returns currently valid `validated` and `canonical` claims for a namespace, optionally filtered by project and text query. Raw and candidate claims are excluded from normal context retrieval.

The minimum agent workflow is:

1. retrieve existing context;
2. execute research or work;
3. submit new or changed claims with evidence;
4. Auditor IA promotes validated material;
5. record outcomes when reality becomes observable;
6. retrieve the updated brain on the next run.

## Obsidian integration

Set:

- `OBSIDIAN_VAULT_PATH`
- `OBSIDIAN_KNOWLEDGE_ROOT` (default `00 - Segundo Cerebro`)

Only `validated` or `canonical` claims can be written to the vault. Export paths are resolved under the configured vault and rejected if they escape it. Writes use a temporary file followed by replacement to avoid partially written notes.

The PostgreSQL knowledge tables remain the operational source of truth. Obsidian is the human-readable knowledge surface, not the transactional database.

## Runtime identities

Bootstrap seeds these canonical agents but leaves them disabled until runtime identity and model policy are provisioned:

- `KNOWLEDGE_IA`: ingest, outcome learning and Obsidian export.
- `AUDITOR_IA`: knowledge promotion, outcome review and Obsidian export.

Optional bindings can be supplied with `KNOWLEDGE_IDENTITY_*` and `AUDITOR_IDENTITY_*` environment variables. As with PMO IA, configuration must be complete or bootstrap fails closed.

## API endpoints

- `POST /api/v1/knowledge/claims` — ingest or merge a claim.
- `GET /api/v1/knowledge/claims` — inspect claims.
- `GET /api/v1/knowledge/claims/{id}` — inspect one claim.
- `POST /api/v1/knowledge/claims/{id}/transition` — advance lifecycle or supersede.
- `GET /api/v1/knowledge/context` — retrieve trusted context for agents.
- `POST /api/v1/knowledge/claims/{id}/outcomes` — record real-world feedback.
- `GET /api/v1/knowledge/claims/{id}/outcomes` — inspect feedback history.
- `GET /api/v1/knowledge/claims/{id}/markdown` — render the Obsidian note without writing.
- `POST /api/v1/knowledge/claims/{id}/export` — write approved knowledge to the configured vault.

## What this version does not yet automate

This version provides the shared knowledge substrate and safe write/read contracts. Continuous autonomous collection still requires workers for Source Hunter, Dataset Scout, knowledge-gap detection, contradiction review and scheduled outcome evaluation. Those workers should use this API rather than create another memory store.
