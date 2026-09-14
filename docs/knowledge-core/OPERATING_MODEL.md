# Universal Knowledge Core — Operating Model

The Second Brain is a shared knowledge service for every current and future project. It is not owned by the Holding project; the Holding is one consumer among many.

## Roles

- Operational agents may submit learnings only as RAW claims.
- Knowledge IA collects, normalizes, deduplicates, links evidence, and prepares candidates.
- Auditor IA independently validates or rejects candidates and is the only autonomous role allowed to promote knowledge toward canonical state.
- Human approval remains required wherever the Control Plane policy already requires it.

## Knowledge lifecycle

`RAW -> CANDIDATE -> VALIDATED -> CANONICAL -> SUPERSEDED`

No agent may write directly to CANONICAL as part of normal execution. Claims keep provenance, evidence, source dates, validity windows, epistemic status, confidence, project scope, namespace and outcome feedback.

## Storage model

PostgreSQL is the operational source of truth for claims, lifecycle, provenance, feedback and audit events. Obsidian is the human-readable knowledge surface. Export to Obsidian is deterministic and optional; absence of a mounted vault must not prevent the knowledge service from operating.

## Feedback loop

Successful agent runs may return a structured `knowledge` array in `output_metadata`. Each item is ingested as RAW and tagged with the originating run and task. This creates a universal write-back path without allowing operational agents to self-certify their conclusions.

## Autonomy routines

The existing Control Plane scheduler should be reused for knowledge routines rather than introducing a parallel scheduler. Planned execution kinds include:

- `knowledge_gap_scan`: identify stale, weakly evidenced or missing knowledge.
- `knowledge_source_scan`: discover candidate sources and datasets.
- `knowledge_outcome_review`: find predictions or hypotheses awaiting result feedback.
- `knowledge_obsidian_sync`: export eligible validated/canonical claims to the configured vault.

Each routine remains subject to the same agent identity, authorization, risk and audit controls as other Control Plane work.
