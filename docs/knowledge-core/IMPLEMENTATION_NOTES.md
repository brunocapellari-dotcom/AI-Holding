# Implementation Notes

The Knowledge Core should stay small and composable. Avoid adding a vector database, graph database, second scheduler, or separate workflow engine until measured requirements justify them. PostgreSQL plus deterministic lifecycle/provenance is the current operational core; additional retrieval/indexing can be layered later without changing governance semantics.
