# Content Factory — Bootstrap do Repositório de Produção

Data: 2026-09-15
Status: pronto para implementação assim que o repositório `Content-Factory` existir.

## 1. Repositório

Nome recomendado: `Content-Factory`
Visibilidade inicial: private
Estratégia: monorepo de produção, sem protótipo descartável.

A AI-Holding guarda governança, padrões compartilhados e links; o código da fábrica permanece no repositório próprio.

## 2. Estrutura alvo

```text
Content-Factory/
  README.md
  pyproject.toml
  package.json
  pnpm-workspace.yaml
  docker-compose.dev.yml
  .env.example
  .github/workflows/
  apps/
    api/
    control-ui/
  workers/
    llm/
    media-cpu/
    media-gpu/
    render/
    publishing/
    qa/
  packages/
    domain/
    schemas/
    orchestration/
    provider-router/
    asset-registry/
    rights-registry/
    continuity-registry/
    brand-registry/
    lineage/
    cost-ledger/
    content-master/
    story-video/
    publishing/
    audiobook/
    course/
    social-connectors/
    security/
    observability/
  renderers/
    remotion/
    pptx/
    typst/
  workflows/
    comfyui/
  infra/
    temporal/
    postgres/
    object-storage/
    otel/
  migrations/
  tests/
    contracts/
    integration/
    adversarial/
    fixtures/full_project/
    e2e_full/
  docs/
    architecture/
    runbooks/
    decisions/
    schemas/
    providers/
    rights/
```

## 3. Runtime

### Python

- Python 3.13+ conforme compatibilidade das dependências
- FastAPI para API/control plane do projeto
- Pydantic v2 para contratos
- SQLAlchemy + Alembic para persistence/migrations
- Temporal Python SDK para workflows/activities
- pytest para testes

### TypeScript/Node

- Node LTS
- Remotion renderer condicionado à licença
- PptxGenJS para PPTX
- clients gerados por OpenAPI/JSON Schema quando útil

Não duplicar regra de negócio entre Python e TypeScript. Renderers recebem render specs tipadas.

## 4. Persistência

PostgreSQL é a fonte de verdade de metadata/estado de negócio.

Tabelas/domínios iniciais:

- tenants
- projects
- brands
- content_masters
- content_master_versions
- claims
- evidences
- assets
- asset_rights
- continuity_entities
- continuity_states
- provider_models
- prompt_workflow_versions
- production_jobs
- production_stages
- derivatives
- publications
- course_masters
- assessments
- lineage_edges
- cost_events
- qa_runs
- qa_findings
- approval_decisions
- audit_events

Object storage mantém media, exports, source packages autorizados e masters. Banco armazena URI, hash e metadata, não blobs pesados.

## 5. IDs e idempotência

Todo job mutável recebe idempotency_key. IDs são opacos/UUID/ULID. Workflows Temporal usam business keys estáveis e não IDs aleatórios por retry.

Publicação deve impedir double-post por plataforma/content derivative/version.

## 6. APIs iniciais

- POST /research-requests
- POST /source-packages/ingest
- POST /content-masters
- POST /content-masters/{id}/versions
- POST /production-jobs
- GET /production-jobs/{id}
- POST /production-jobs/{id}/approve
- GET /assets/{id}
- GET /lineage/{id}
- GET /costs
- GET /qa-runs/{id}
- POST /exports

Research request deve usar o contrato canônico do Research AI; a Content Factory não pesquisa por conta própria.

## 7. Workflow E2E_FULL

Temporal Workflow `FullContentProductionWorkflow` coordena:

1. validate_input
2. resolve_knowledge_snapshot
3. build_content_master
4. validate_claims
5. editorial_plan
6. story_video_plan
7. resolve_assets
8. visual_generation
9. voice_generation
10. long_video_render
11. short_render
12. article_render
13. manuscript_render
14. epub_render
15. epub_validate
16. pdf_render
17. audiobook_render
18. course_master_build
19. lesson_build
20. slides_render
21. quiz_build
22. content_qa
23. rights_qa
24. provenance_qa
25. cost_reconcile
26. approval_gate
27. publication_package
28. finalize_lineage

Cada Activity é retry-safe e declara side effects. Publicação externa é Activity separada e idempotente.

## 8. Provider Router

Interfaces separadas por capability:

- LLMProvider
- ImageProvider
- VideoProvider
- TTSProvider
- STTProvider
- MusicSFXProvider
- StorageProvider
- SocialPublisher
- LMSExporter

Seleção recebe policy + cost ceiling + rights requirement + quality profile + privacy class. Nenhum workflow usa nome de modelo diretamente.

## 9. Security baseline

Obrigatório no primeiro commit operacional:

- MIME/magic validation
- upload quarantine
- archive bomb/path traversal defenses
- sandbox media/document processing
- egress allowlist para fetchers autorizados
- URL parser + SSRF deny ranges
- command invocation sem shell interpolation
- secrets apenas via mecanismo aprovado
- structured logs com secret/PII redaction
- tenant authorization
- dependency lockfiles
- SBOM
- Trivy/Semgrep/Gitleaks
- signed artifacts/images quando possível

## 10. CI/CD

Pipeline mínimo:

1. format/lint/typecheck
2. unit/contract tests
3. dependency/license gate
4. Semgrep/Gitleaks
5. SBOM/Syft
6. Trivy
7. promptfoo evals/red-team
8. build containers/renderers
9. integration tests
10. E2E_FULL completo
11. provenance/signing
12. deploy staging
13. smoke + E2E_FULL staging
14. promotion somente se gates passarem

Não reduzir E2E_FULL em PR/release por custo sem criar uma classe explícita de `PR_FAST` que nunca tenha autoridade para declarar release operacional.

## 11. Observabilidade

OpenTelemetry em API, workflows e workers. Correlation IDs: tenant_id, project_id, content_master_id, production_job_id, workflow_id, stage_id. LLM/media/provider calls devem registrar provider/model version, latency, attempts e cost sem salvar secrets.

## 12. Dados de teste

Criar fixture `tests/fixtures/full_project/` com conteúdo próprio/licenciado, brand fictícia e claims verificáveis. A mesma fixture deve exercitar todos os produtos finais.

Criar segunda fixture adversarial com HTML/SVG/archive/URLs/documentos maliciosos e cross-tenant attempts.

## 13. Definition of Done do bootstrap

O bootstrap termina apenas quando:

- repo criado
- estrutura acima materializada
- migrations aplicam do zero
- Temporal inicia
- object storage e Postgres funcionam
- API health e workflow start funcionam
- provider mock + pelo menos um provider real por capability essencial
- renderers reais geram artifacts
- E2E_FULL produz todos os formatos
- security/adversarial suite passa
- cost/rights/lineage/QA ficam persistidos
- CI bloqueia regressão

A partir daí o projeto é uma plataforma operacional evolutiva; novos modelos/providers entram por adapters e benchmarks sem redesenhar o core.