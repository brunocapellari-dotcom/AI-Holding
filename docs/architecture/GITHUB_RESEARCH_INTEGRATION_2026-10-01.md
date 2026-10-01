# GitHub Research Integration — 2026-10-01

Status: CANONICAL ADDENDUM

This addendum consolidates the GitHub research rounds performed on 2026-10-01. It extends the consolidated Holding architecture without replacing existing canonical documents.

## Governing rule

External repositories are not adopted by popularity. Every candidate is classified as:

- `ADOPT`: approved capability/component, still subject to security/license intake.
- `POC`: controlled proof before production.
- `ADAPT`: absorb selected architecture, algorithms, contracts or workflow patterns.
- `REFERENCE`: study only; do not create a production dependency by default.
- `RESERVE`: retain for a future scale/capability threshold.
- `REJECT`: redundant, incompatible or unjustified.

Before any runtime promotion: license, maintenance, security, provenance, rollback, observability, tests and exit strategy are mandatory.

## Shared platform capabilities

### Hermes Development Factory

Adopt the following architecture:

`Change Contract -> independent plan review -> isolated worktree -> implementation -> deterministic verification -> independent inspection -> security gate -> evidence -> merge`.

Sources/patterns:

- OpenSpec — ADAPT for proposal/spec/design/tasks and verifiable acceptance criteria.
- Claudex Loop — ADAPT for Claude Code <-> Codex independent review.
- Worktrunk — POC for isolated Git worktrees per agent/task.
- gstack — ADAPT selected planning/review/QA/security/release skills.
- shadcn/improve — ADAPT evidence-backed repo audit, self-contained plans, verification gates and STOP conditions.
- Ponytail — ADAPT minimal-implementation ladder before adding code/dependencies.
- Dagger — POC for portable build/test/package/release execution across local, sandbox, CI and Google Cloud.
- Serena — REFERENCE/isolated development tool; use LSP/AST ideas for owned code intelligence.
- Graphify — POC for source-backed code/knowledge graph where license and security gates pass.
- OpenWiki — POC as derived repository wiki with claims tied to source evidence.

No engineering agent may mark a task complete without machine-verifiable acceptance evidence.

### Agent Runtime and Governance

Create one shared Agent Manifest contract with six mandatory sections:

1. ENTRY — accepted channels and inputs.
2. INSTRUCTIONS — mission, objectives and rules.
3. KNOWLEDGE — approved context sources and retrieval.
4. TOOLS — allowed tools and scopes.
5. TRIGGERS — events, schedules and conditions.
6. LIMITS — prohibited actions, approvals, budgets, rate limits and timeouts.

Add:

- Hermes Action Firewall — ADAPT Cordum/OpenWorker patterns: ALLOW / REQUIRE_APPROVAL / DENY.
- Earned autonomy with hard floors; no prompt may override policy.
- Approval provenance for every consequential tool call.
- Circuit breaker for repeated denials/anomalies.
- Execution sandbox benchmark: OpenSandbox x OpenShell.
- FastMCP — POC as Hermes Tool SDK.
- ContextForge / Archestra / MCP Gateway Registry — ADAPT gateway, identity, routing, registry and governance patterns.

### Security and supply chain

The shared Security Gate must combine, not duplicate, scanners by layer:

- SkillSpector — agent skill inspection.
- Cisco MCP Scanner — MCP server/tool inspection.
- NVIDIA garak — LLM red-team and vulnerability evaluation.
- OSV-Scanner — dependency/container vulnerabilities.
- OpenSSF Scorecard — upstream project posture.
- Gitleaks — secrets.
- Semgrep/OpenGrep benchmark — SAST.
- Syft/CycloneDX/SPDX — SBOM.
- Cosign/SLSA/in-toto — artifact provenance where applicable.
- GUAC — POC for a supply-chain security graph that links artifacts, SBOMs, vulnerabilities and provenance.

### MCP Quality Gate

Before a new MCP server reaches the Tool Registry:

`build -> static/security scan -> official MCP Inspector -> MCPJam cross-client/model tests -> scenario regression -> registry promotion`.

### Evaluation and observability

- OpenTelemetry is the neutral telemetry standard.
- OpenLLMetry — ADAPT for LLM/agent instrumentation.
- Phoenix/Langfuse/Helicone/AgentOps remain backend candidates; instrumentation must not depend on one backend.
- Promptfoo — prompt/model regression.
- LangWatch Scenario — multi-turn behavior scenarios.
- Inspect AI — broader capability/evaluation suites.
- Execution replay must preserve task, model, tools, timings, cost, artifacts, errors, approvals and evidence.

### Knowledge/context infrastructure

Keep canonical truth separate from retrieval/derived views:

- Second Brain/approved Markdown + governed PostgreSQL = canonical knowledge.
- CocoIndex — POC for incremental delta-only context/index refresh.
- QMD — POC/local retrieval over Markdown/docs/transcripts.
- Graphify — POC derived relationship graph.
- OpenWiki — POC derived source-grounded repo documentation.
- Cognee / Neo4j Agent Memory — REFERENCE for session distillation/reasoning memory.
- LLMLingua — BENCHMARK only; promote only if quality is preserved while cost/latency improves.
- LMCache — RESERVE for future high-volume local/open-model inference.

### Research and source discovery

Research AI owns:

- Source Scout / API Radar.
- Repo Intelligence.
- Skill Factory.
- Source Adapter Factory.
- Research Strategy Engine.
- Scientific Evidence Engine.
- Research Data Refinery.

Discovery sources may include Public APIs catalog, awesome-mcp-servers, GitHub, OpenAlex, Crossref, Semantic Scholar, CKAN/Socrata/STAC/OpenAPI catalogs. Discovery never equals approval.

### Shared data/multimodal capabilities

- Hamilton + Ibis — POC for portable feature/data graphs.
- Daft x Pixeltable — benchmark for multimodal processing/persistence.
- Docling remains primary parser; MinerU/Marker/Unlimited-OCR/ExtractThinker are benchmark/specialist candidates.
- TiTiler + TiPG + Martin — shared GeoIntel serving stack by raster/vector role.
- Dagger handles portable engineering pipelines, not business workflow orchestration.

## Portfolio rule

Do not create one repository for each discovered tool. Shared capabilities belong under Holding/Hermes/Research/Second Brain unless they contain domain-specific business logic.

Project-specific additions are maintained in each repository's 2026-10-01 integration addendum.
