# Research AI — Gap Analysis

Data de corte: 2026-09-15

## Escopo auditado

O repositório `AI-Holding` já contém Control Plane, PostgreSQL operacional, identidade, auditoria, políticas, rotinas, scheduler, workers, Knowledge Core, segurança de supply chain, CI e observabilidade básica. Research AI deve consumir esses serviços compartilhados, não recriá-los.

## O que já existe e será reutilizado

- Control Plane: projetos, tarefas, agentes, runs, decisões, incidentes e audit log.
- Cloud SQL PostgreSQL 16 como estado operacional canônico.
- Cloud Run, Artifact Registry, Secret Manager, VPC privada e Workload Identity.
- Cloud Scheduler para disparos de alto nível.
- Knowledge Core / Segundo Cérebro como destino de conhecimento validado.
- Open Source Intake Gate com Scorecard, ORT/licença, Syft, Gitleaks, Semgrep, Trivy e Cosign.
- pytest, coverage >= 90%, Ruff, mypy strict, Bandit e pip-audit.
- métricas Prometheus e logging estruturado.

## Lacunas reais

### P0 — bloqueiam a operação E2E

1. Não existe repositório/unidade deployável `Research-AI`.
2. Não existe contrato executável de `ResearchRequest` e `ResearchPackage`.
3. Não existe motor de discovery multi-fonte.
4. Não existe crawler/browser isolado para conteúdo web não confiável.
5. Não existe registry de Source, Snapshot, Evidence, Claim, API, Dataset e RepositoryCandidate.
6. Não existe pipeline de download em quarentena com hash, MIME, inspeção de archive e malware scan.
7. Não existe orquestração durável de ResearchRun com retry, timeout, resume, cancelamento e idempotência.
8. Não existe teste E2E real que atravesse discovery → coleta → verificação → teste → análise → package → handoff.

### P1 — necessárias para versão final

1. Source Health Engine.
2. Deduplicação e canonicalização de URLs, DOI, ISBN, GitHub repos e assets.
3. Entity resolution para organizações/autores/provedores.
4. Temporal model: `published_at`, `observed_at`, `retrieved_at`, `valid_from`, `valid_until`, `source_version`.
5. Evidence/provenance chain reproduzível.
6. License Audit e rights policy por artefato.
7. Security Audit de APIs, downloads e componentes GitHub.
8. Dataset profiler e validation engine.
9. API probe engine para REST, GraphQL, WebSocket, MCP, STAC, CKAN/Socrata, RSS/Atom, FTP/SFTP e bulk download.
10. Research Budget Controller: custo, profundidade, timeout e limite de fontes.
11. Novelty/Relevance Gate para impedir watchers de criarem ruído.
12. Observabilidade OpenTelemetry com traces por `request_id`/`research_run_id`.
13. Handoff versionado para Knowledge Factory e projetos consumidores.

## Redundâncias a evitar

- Não criar segundo PostgreSQL: usar instância compartilhada, com schema/usuário isolado de Research AI.
- Não criar segundo Secret Manager.
- Não criar segundo scheduler: Cloud Scheduler dispara watchers; workflow engine controla execução durável.
- Não criar segundo Knowledge Core ou RAG canônico.
- Não criar múltiplos crawlers principais.
- Não instalar múltiplos parsers para o mesmo MIME sem roteamento explícito.
- Não usar LangChain + LangGraph + PydanticAI simultaneamente.
- Não criar Elasticsearch/OpenSearch enquanto PostgreSQL JSONB/FTS e armazenamento de objetos satisfizerem o volume.
- Não copiar código das unidades para o Control Plane.

## Fronteira final

`AI-Holding` governa. `Research AI` pesquisa e entrega evidência. `Knowledge Factory` transforma evidência em claims validados. `Segundo Cérebro` mantém conhecimento canônico.

## Bloqueio externo identificado

O conector GitHub disponível nesta sessão permite branch, arquivos, commits, issues e pull requests, mas não criação de repositório. O repositório independente `brunocapellari-dotcom/Research-AI` precisa ser criado fora desta ação antes do bootstrap do serviço. Não será contornada essa limitação colocando o código da unidade dentro de `AI-Holding`, pois o README da Holding exige independência entre Control Plane e código das unidades.
