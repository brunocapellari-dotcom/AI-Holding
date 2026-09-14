# Project Integration Pattern

Each project should integrate with the Second Brain through the same contract:

1. Read validated/canonical context using its allowed namespaces.
2. Execute work against live project data and tools.
3. Return reusable conclusions in `output_metadata.knowledge`.
4. Let the Knowledge Core ingest those contributions as RAW.
5. Let Knowledge IA and Auditor IA independently curate and validate.
6. Record later outcomes for predictions/hypotheses so confidence can be calibrated.

Projects must not create independent knowledge stores unless required for a specialized raw-data workload. Shared reusable knowledge belongs in the Universal Knowledge Core.
