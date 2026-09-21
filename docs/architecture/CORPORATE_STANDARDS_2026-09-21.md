# Corporate Standards — Holding Digital / AI OS

Date: 2026-09-21
Status: canonical cross-project standard

## Principle

Transversal capabilities are corporate infrastructure. Individual projects MUST NOT create an
independent toolchain, registry, evaluation stack, dependency bot, data-contract dialect, model
catalog or MCP governance layer without an approved Architecture Decision Record (ADR) that
demonstrates a technical requirement the shared standard cannot satisfy.

The Holding governs the standard. Domain projects contribute requirements and evidence.

## Mandatory corporate registries

The Registry Directory is the index of the ten mandatory registries and identifies the owner and
source of truth for each one.

| Registry | Canonical owner | Source of truth |
|---|---|---|
| Tool Registry | Holding | `tool_registry` |
| Source Registry | Holding governance; Research AI proposes/discovers | `source_registry` |
| License Registry | Holding | `license_registry` |
| Model Registry | Hermes governance | `model_registry` in Holding; Hermes consumes it at runtime |
| Evaluation Registry | Holding Auditor | `evaluation_registry` |
| Risk Registry | Holding | existing `risk_registry` |
| Cost Registry | Holding FinOps | existing `cost_entries` |
| Architecture Decision Registry | Holding Architecture | Git documents under `docs/architecture`, indexed in DB |
| Data Contract Registry | Holding Data Governance | Git contracts + `data_contract_registry` index/results |
| Project Registry | Holding | existing projects + operational profiles |

Research AI may discover candidate sources but does not maintain a second canonical Source
Registry. Hermes may enrich/runtime-route models but does not maintain a second governance truth.
Phoenix stores trace/evaluation artifacts; Promptfoo produces CI evaluation artifacts; the
Evaluation Registry stores the governed definition, gate and latest evidence reference rather than
copying all raw artifacts.

## Corporate development toolchain

### mise — ADOPT

One root `mise.toml` declares tool versions and common tasks. It is the corporate entry point for
developer/CI tool versions, environment bootstrap and project commands. Projects may add
project-specific tasks but MUST NOT adopt a second version manager without ADR.

### uv — ADOPT

uv is the canonical Python dependency resolver/environment/lock workflow. The target state is:

`pyproject.toml -> uv.lock -> uv sync --locked`

The lockfile is committed. No Poetry/Pipenv/requirements lock may become a parallel source of
truth. Exported requirements/SBOM files are derived artifacts.

### Ruff — KEEP / corporate Python standard

Ruff is the default lint and format tool. A project may extend rules, but replacing Ruff requires
an ADR.

### pre-commit — ADOPT

pre-commit is a local orchestration layer only. Hooks call the same Ruff/MyPy/full-project gate
commands used elsewhere. It MUST NOT introduce a second lint/format/test implementation.

### Renovate — ADOPT, replacing Dependabot

Renovate is the dependency-maintenance standard. The configuration requires:

- dependency cooldown via `minimumReleaseAge`;
- `internalChecksFilter=strict`;
- Dependency Dashboard;
- explicit approval and human review for major upgrades;
- no automatic merge for Python, Terraform, Docker, GitHub Actions or mise dependencies;
- uv lockfile maintenance.

For this private repository the preferred operating model is the hosted Renovate GitHub App rather
than embedding the AGPL Renovate runtime in product infrastructure. Dependabot configuration is
removed to prevent duplicate PR generation.

## AI observability and evaluation

### OpenTelemetry — transport standard

OpenTelemetry remains the vendor-neutral telemetry transport. AI tooling must integrate through
OTel/OpenInference where possible.

### Phoenix — ADOPT with license boundary

Phoenix is the standard UI/store for AI traces, datasets, experiments and trace-based evaluation.
It is ELv2. Approved use is internal/self-hosted observability. Do not embed Phoenix into a
commercial product or expose substantial Phoenix functionality as a managed service without a new
license review.

Phoenix does not replace the Holding Evaluation Registry. The registry holds governance metadata
and gate status; Phoenix holds detailed trace/evaluation artifacts.

### Promptfoo — ADOPT

Promptfoo is the standard deterministic LLM/agent regression, red-team and MCP security test
runner. It belongs in CI/Security Test Lab, not as production observability.

Defaults:
- telemetry/cloud sharing disabled unless explicitly authorized;
- configs/providers treated as executable code;
- generated adversarial data treated as untrusted;
- result artifacts referenced by the Evaluation Registry;
- regressions fail the promotion gate.

Phoenix + Promptfoo are complementary, not parallel evaluation truths.

## Data quality and Data Contracts

The canonical contract format is `holding-data-contract-v1`. It is vendor-neutral and stored in
Git; execution results are indexed by the Data Contract Registry.

### Soda Core — BENCHMARK

Soda may be used as an execution adapter when it provides useful checks against supported
datastores. It is not the canonical contract language because:
- Soda contract support has changed between versions and is documented as beta/experimental in
  parts of the current documentation;
- Soda Core is ELv2;
- the Holding must preserve portable contracts if Soda is replaced.

A project can use a Soda adapter only when the native contract remains complete and auditable.

## MCP governance

### ToolHive — BENCHMARK / compatibility target

ToolHive is Apache-2.0 and provides strong primitives for MCP registry, isolation, OIDC/policy,
gateway enforcement, audit and OpenTelemetry.

Do not deploy the entire ToolHive platform merely because these features exist. The corporate
sequence is:

1. keep Tool Registry and authorization truth in the Holding/Hermes architecture;
2. make MCP registrations exportable/compatible with the official MCP Registry API;
3. benchmark ToolHive Registry Server and Gateway against our requirements;
4. adopt ToolHive components only when they replace custom code or materially reduce security
   risk/maintenance;
5. never create a second Holding or Hermes control plane.

## Project Control Plane

### Plane — BENCHMARK

Plane remains a candidate/reference for project UI and work-management capabilities: projects,
work items, cycles, modules, webhooks, REST API and MCP.

It MUST NOT run as a parallel source of truth beside Holding Project/Task/PMO. Adoption requires a
replacement ADR showing:
- what existing Holding capability Plane replaces;
- data migration and rollback;
- API ownership;
- security/identity integration;
- AGPL implications;
- no duplicate task/project state.

Until then, use Plane concepts and API design as reference only.

## License policy

License Registry classifications are mandatory before a corporate tool becomes approved.

Default policy:
- MIT / Apache-2.0 / similarly permissive: approved subject to notices;
- weak copyleft: review;
- AGPL/strong copyleft: conditional and requires architectural/legal review for embedded or
  network-service use;
- ELv2/source-available: conditional; internal use may be allowed, managed-service exposure is not
  assumed;
- proprietary/managed service: explicit commercial/data/security review;
- unknown: cannot be promoted to approved.

The automated dependency license gate remains a release gate, but the License Registry is the
governance source for exceptions and non-package tooling.

## Exceptions

A project may diverge only when an ADR records:
1. the exact capability gap;
2. alternatives benchmarked;
3. license/security/data implications;
4. operating and migration cost;
5. source-of-truth impact;
6. migration and rollback;
7. evaluation evidence;
8. independent audit result.

"Team preference" or "different stack per project" is not sufficient justification.
