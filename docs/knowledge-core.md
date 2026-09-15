# Universal Knowledge Core

The Universal Knowledge Core is the shared memory and learning layer for every current and future project. It is not owned by the AI Holding domain; the Holding is one consumer of the same brain used by AgroLog MT, Mercado Financeiro, Inteligência Esportiva, Geopolitical Watch and other projects.

## Operating model

Each project can publish structured claims into controlled namespaces. A claim stores the statement, source, evidence locators, epistemic status, confidence, validity window, project provenance and creating agent. The lifecycle is deliberately gated:

`raw -> candidate -> validated -> canonical -> superseded`

Operational agents can contribute only RAW knowledge. Knowledge IA collects, normalizes, merges evidence and prepares candidates. Auditor IA owns independent promotion. This separation prevents an agent from researching a conclusion and certifying the same conclusion as canonical truth.

Canonical means approved for reuse under the current evidence and validity window, not permanently true. Canonical knowledge can expire or be superseded while the historical record remains queryable.

## Epistemic status

Claims are classified independently from lifecycle as:

- `observed`: directly observed from a source or measurement.
- `estimated`: estimated from observed inputs.
- `projected`: forward-looking projection.
- `inferred`: analytical inference from evidence.
- `structural`: durable methodology, definition or domain knowledge.

A projected claim can therefore be canonical as the canonical record of a forecast without being misrepresented as an observation.

## Deduplication and contradiction handling

Ingestion normalizes whitespace and case, computes a SHA-256 fingerprint and deduplicates within each namespace. Re-ingestion merges new evidence and tags instead of creating another copy. A conflicting incoming epistemic classification is recorded in metadata for audit rather than silently replacing the stored classification.

A canonical claim may supersede another claim in the same namespace. The prior claim remains stored as `superseded`, preserving the historical chain.

## Universal agent write-back

A successful run can return reusable learning inside `Run.output_metadata.knowledge`. Each valid contribution is automatically ingested as RAW and tagged with its originating project, task, run and execution kind. Invalid contributions are ignored rather than causing a successful operational execution to fail.

Example:

```json
{
  "knowledge": [
    {
      "namespace": "agrolog.market",
      "statement": "Reusable factual or analytical conclusion produced by the run.",
      "epistemic_status": "inferred",
      "confidence": 82,
      "source_name": "primary-source-or-run",
      "source_uri": "https://example.com/source",
      "evidence": [
        {
          "source": "primary-source",
          "locator": "table/page/record identifier",
          "uri": "https://example.com/source"
        }
      ]
    }
  ]
}
```

Confidence is stored on a 0–100 scale. For compatibility, write-back also accepts a fractional value from 0 to 1 and converts it to the 0–100 scale. Confidence never promotes a claim automatically.

The run records `knowledge_capture.status` and `knowledge_capture.created_claims` in its output metadata. Database errors in the knowledge side effect are isolated with a savepoint so a completed operational run is not converted into a failed run by an auxiliary memory write.

## Outcome learning

Claims can receive outcome records with verdicts:

- `confirmed`
- `partially_confirmed`
- `refuted`
- `inconclusive`

An outcome stores the observed result, optional numeric error metric and evidence. Outcome counters are attached to claim metadata. This creates the closed feedback loop needed for later calibration, post-mortems and autonomy scoring. Outcome recording does not automatically rewrite confidence or promote/demote knowledge; those policies remain auditable and deterministic.

## Gap detection

The initial deterministic gap scanner can identify non-superseded claims that are expired, have confidence below 60, or have no structured evidence. It is intentionally a small service over PostgreSQL and does not introduce a second scheduler, vector database or graph database.

The next execution layer should reuse the Control Plane scheduler for recurring gap review, outcome review, source/dataset discovery and Obsidian synchronization.

## Retrieval contract

Agents should query `GET /api/v1/knowledge/context` before material work. This endpoint only returns currently valid `validated` and `canonical` claims for a namespace, optionally filtered by project and text query. Raw and candidate claims are excluded from trusted context retrieval.

The minimum project workflow is:

1. retrieve existing trusted context;
2. execute work against current project data and tools;
3. return reusable learning through the run write-back contract or submit claims directly;
4. Knowledge IA curates candidates;
5. Auditor IA independently validates/promotes;
6. record outcomes when reality becomes observable;
7. retrieve the updated brain on the next run.

Projects may keep specialized raw analytical or operational databases, but reusable cross-project knowledge should not be duplicated into parallel brains.

## Obsidian integration

Set:

- `OBSIDIAN_VAULT_PATH`
- `OBSIDIAN_KNOWLEDGE_ROOT` (default `00 - Segundo Cerebro`)

Only `validated` or `canonical` claims can be written to the vault. Export paths are resolved under the configured vault and rejected if they escape it. Writes use a temporary file followed by replacement to avoid partially written notes.

PostgreSQL remains the operational source of truth for claims, lifecycle, provenance, outcomes and audit. Obsidian is the human-readable knowledge surface, not the transactional database.

## Runtime identities

Bootstrap seeds these canonical agents but leaves them disabled until runtime identity and model policy are provisioned:

- `KNOWLEDGE_IA`: ingest, outcome learning and Obsidian export.
- `AUDITOR_IA`: knowledge promotion, outcome review and Obsidian export.

Optional bindings can be supplied with `KNOWLEDGE_IDENTITY_*` and `AUDITOR_IDENTITY_*` environment variables. Configuration must be complete or bootstrap fails closed.

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

## Security boundaries

- Operational agents cannot self-promote their learning.
- Canonical promotion stays under separate authorization.
- Knowledge mutations are auditable through the Control Plane.
- Obsidian export cannot escape the configured vault root.
- Source URIs and evidence are treated as data, never executable instructions.
- Secrets and connector credentials must not be stored in claims or exported Markdown.
- External acquisition must respect access controls and source licensing.

## Remaining automation

The substrate and universal run write-back are implemented. The remaining autonomous layer is to support scheduled execution kinds for gap review, source/dataset discovery, outcome review and Obsidian synchronization, then provision the Knowledge IA and Auditor IA runtimes against those execution kinds. These should reuse the existing Control Plane scheduler and policy engine rather than create a parallel orchestration stack.
