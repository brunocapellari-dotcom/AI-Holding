# Research AI — Contratos Canônicos

Data de corte: 2026-09-15

Os contratos abaixo devem virar Pydantic models + JSON Schema no repositório `Research-AI`. IDs são UUID/ULID; timestamps são UTC ISO-8601; URLs são normalizadas, mas o valor original é preservado na proveniência.

## ResearchRequest

```yaml
request_id: string
project: string
domain: string
question: string
desired_output: [string]
urgency: low|normal|high|critical
freshness:
  max_age_seconds: integer|null
  as_of: datetime|null
source_preferences:
  prefer_primary: true
  include_domains: [string]
  exclude_domains: [string]
  preferred_source_types: [string]
geography: [string]
time_range:
  start: datetime|null
  end: datetime|null
restrictions:
  allowed_access: [PUBLIC, AUTHENTICATED, LICENSED, INTERNAL]
  prohibited_actions: [string]
  max_cost_usd: number|null
  max_runtime_seconds: integer|null
  max_sources: integer|null
  allow_downloads: boolean
  allow_api_probe: boolean
  allow_browser: boolean
requested_by: string
created_at: datetime
idempotency_key: string
```

## Source

```yaml
source_id: string
canonical_name: string
organization: string|null
canonical_url: string
type: WEB|NEWS|GOVERNMENT|ACADEMIC|API|DATASET|GITHUB|VIDEO|BOOK|DOCUMENT|RSS|OTHER
domains: [string]
projects: [string]
official: boolean
primary_source: boolean
access: PUBLIC|AUTHENTICATED|LICENSED|INTERNAL|RESTRICTED|PROHIBITED
auth_type: NONE|API_KEY|OAUTH|BASIC|SIGNED|OTHER
cost_model: string|null
license_spdx: string|null
terms_url: string|null
quality_profile: object
collector: string|null
last_checked_at: datetime|null
health_status: HEALTHY|DEGRADED|BROKEN|UNKNOWN
metadata: object
```

## SourceSnapshot

```yaml
snapshot_id: string
source_id: string
original_url: string
resolved_url: string
published_at: datetime|null
effective_at: datetime|null
observed_at: datetime|null
retrieved_at: datetime
valid_from: datetime|null
valid_until: datetime|null
source_version: string|null
http_status: integer|null
etag: string|null
last_modified: datetime|null
mime_declared: string|null
mime_detected: string|null
content_length: integer|null
sha256: string
storage_uri: string|null
rights_status: ALLOWED|CONDITIONAL|UNKNOWN|BLOCKED
security_status: CLEAN|SUSPICIOUS|BLOCKED|NOT_APPLICABLE
parser_version: string|null
provenance: object
```

## Evidence

```yaml
evidence_id: string
snapshot_id: string
locator:
  page: integer|null
  section: string|null
  lines: [integer]|null
  timecode_start: number|null
  timecode_end: number|null
  json_pointer: string|null
  table: string|null
excerpt_hash: string|null
supports_claim: boolean
relevance: number
notes: string|null
```

## Claim

```yaml
claim_id: string
research_run_id: string
statement: string
claim_type: FACT|ESTIMATE|PROJECTION|INFERENCE|RECOMMENDATION
subject_entities: [string]
reference_time: datetime|null
evidence_ids: [string]
contradiction_ids: [string]
quality:
  authority: number
  primary_source: number
  freshness: number
  directness: number
  independence: number
  coverage: number
  reproducibility: number
status: SUPPORTED|PARTIALLY_SUPPORTED|CONTESTED|UNSUPPORTED
```

## Contradiction

```yaml
contradiction_id: string
claim_id: string
evidence_ids: [string]
type: VALUE_CONFLICT|DATE_CONFLICT|DEFINITION_CONFLICT|METHODOLOGY_CONFLICT|VERSION_CONFLICT|OTHER
explanation: string
resolution: UNRESOLVED|TEMPORAL|METHODOLOGICAL|SOURCE_PRIORITY|CORRECTED
preferred_evidence_id: string|null
resolution_reason: string|null
```

## ApiCandidate

```yaml
api_id: string
provider: string
official: boolean
protocol: REST|GRAPHQL|WEBSOCKET|MCP|STAC|FTP|SFTP|RSS|OTHER
base_url: string
documentation_url: string|null
auth: object
rate_limit: object|null
pagination: object|null
schema: object|null
coverage: object|null
update_frequency: string|null
cost: object|null
license: object|null
terms: object|null
sample_request_redacted: object|null
sample_response_hash: string|null
last_tested_at: datetime|null
test_status: PASS|PARTIAL|FAIL|NOT_TESTED
latency_ms: number|null
integration_status: USE|ADAPT|REFERENCE|REJECT
```

## DatasetCandidate

```yaml
dataset_id: string
provider: string
subject: [string]
format: [string]
granularity: string|null
coverage: object
start_date: datetime|null
end_date: datetime|null
update_frequency: string|null
license: object|null
download_method: string|null
api_id: string|null
size_bytes: integer|null
quality: object
known_limitations: [string]
last_profiled_at: datetime|null
```

## RepositoryCandidate

```yaml
repository_id: string
full_name: string
url: string
purpose: string
capabilities: [string]
stars: integer|null
forks: integer|null
last_push_at: datetime|null
last_release: string|null
language: string|null
architecture: string|null
license_spdx: string|null
security: object
maintenance: object
interesting_components: [string]
dependencies: object|null
commercial_risk: LOW|MEDIUM|HIGH|UNKNOWN
recommendation: USE|ADAPT|REFERENCE|REJECT
recommendation_reason: string
checked_at: datetime
```

## LicenseAssessment

```yaml
assessment_id: string
subject_type: CODE|MODEL|DATASET|API|DOCUMENT|MEDIA|OTHER
subject_id: string
license_detected: string|null
terms_url: string|null
commercial_use: ALLOWED|CONDITIONAL|BLOCKED|UNKNOWN
modification: ALLOWED|CONDITIONAL|BLOCKED|UNKNOWN
redistribution: ALLOWED|CONDITIONAL|BLOCKED|UNKNOWN
storage: ALLOWED|CONDITIONAL|BLOCKED|UNKNOWN
attribution_required: boolean
share_alike_or_source_obligation: boolean
notes: [string]
assessed_at: datetime
```

## SecurityAssessment

```yaml
assessment_id: string
subject_type: URL|DOWNLOAD|ARCHIVE|REPOSITORY|API|PACKAGE|CONTAINER
subject_id: string
ssrf_check: PASS|FAIL|NA
mime_check: PASS|FAIL|NA
malware_scan: PASS|FAIL|NA
archive_scan: PASS|FAIL|NA
supply_chain_gate: PASS|FAIL|NA
prompt_injection_risk: LOW|MEDIUM|HIGH|NA
secrets_exposure: PASS|FAIL|NA
result: PASS|CONDITIONAL|BLOCKED
findings: [string]
assessed_at: datetime
```

## ResearchPackage

```yaml
package_id: string
request_id: string
research_run_id: string
project: string
question: string
executive_summary: string
findings: [object]
claim_ids: [string]
source_ids: [string]
contradiction_ids: [string]
uncertainties: [string]
recommended_source_ids: [string]
api_ids: [string]
dataset_ids: [string]
repository_ids: [string]
download_asset_ids: [string]
license_assessment_ids: [string]
security_assessment_ids: [string]
next_actions: [object]
quality_summary: object
coverage:
  citation_coverage: number
  primary_source_ratio: number
  source_diversity: object
  freshness: object
created_at: datetime
package_version: string
content_sha256: string
audit_status: PASS|PASS_WITH_NOTES|FAIL
```

## ResearchAudit

```yaml
audit_id: string
package_id: string
auditor: string
independent_from_synthesis: true
checks:
  request_satisfied: PASS|FAIL
  citation_coverage: PASS|FAIL
  contradictions_exposed: PASS|FAIL
  temporal_consistency: PASS|FAIL
  source_quality: PASS|FAIL
  license_compliance: PASS|FAIL
  security_compliance: PASS|FAIL
  reproducibility: PASS|FAIL
  unsupported_claims: PASS|FAIL
result: PASS|PASS_WITH_NOTES|FAIL
findings: [string]
audited_at: datetime
```

## Eventos de integração

- `research.request.accepted`
- `research.run.started`
- `research.run.partial`
- `research.run.failed`
- `research.package.ready`
- `research.package.rejected`
- `research.source.degraded`
- `research.source.broken`
- `research.component.superior_candidate`

Todo evento contém `event_id`, `event_version`, `occurred_at`, `request_id`, `research_run_id` quando aplicável, `project`, `actor` e `trace_id`.
