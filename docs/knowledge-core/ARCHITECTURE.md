# Universal Knowledge Core Architecture

```text
Operational Agents
      |
      | successful run output_metadata.knowledge
      v
RAW Knowledge Claims
      |
      v
Knowledge IA
normalize / dedupe / connect evidence / identify gaps
      |
      v
CANDIDATE
      |
      v
Auditor IA
independent validation
      |
      v
VALIDATED -> CANONICAL -> SUPERSEDED
      |
      +--> PostgreSQL operational truth
      +--> Obsidian human-readable projection
      +--> project context retrieval
      +--> outcome feedback / calibration
```

The Control Plane remains responsible for identity, authorization, audit, task scheduling and execution policy. The Knowledge Core adds knowledge semantics; it does not replace the Control Plane.
