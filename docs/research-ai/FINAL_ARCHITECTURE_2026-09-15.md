# Research AI — Arquitetura Final

Data de corte: 2026-09-15
Status: arquitetura-alvo definitiva; sem MVP descartável.

## Missão

Research AI é a infraestrutura central de pesquisa para todos os projetos. Recebe uma necessidade, planeja a investigação, descobre fontes, coleta evidência, testa APIs/datasets/software quando permitido, verifica qualidade/licença/segurança, produz um `ResearchPackage` reproduzível e entrega ao projeto solicitante e à Knowledge Factory.

Research AI não grava verdade canônica diretamente no Segundo Cérebro.

## Pipeline obrigatório

`RESEARCH_REQUEST → QUERY_PLAN → DISCOVERY → SOURCE_COLLECTION → QUALITY_FILTER → CROSS_CHECK → RIGHTS_SECURITY_GATE → DOWNLOAD_OR_TEST → ANALYSIS → INDEPENDENT_AUDIT → RESEARCH_PACKAGE → PROJECT + KNOWLEDGE_FACTORY`

Estados formais:

`RECEIVED`, `PLANNED`, `DISCOVERING`, `COLLECTING`, `VERIFYING`, `TESTING`, `ANALYZING`, `AUDITING`, `PACKAGED`, `DELIVERED`, `PARTIAL`, `BLOCKED_AUTH`, `BLOCKED_LICENSE`, `SECURITY_REJECTED`, `SOURCE_UNAVAILABLE`, `INSUFFICIENT_EVIDENCE`, `FAILED`, `CANCELLED`.

## Arquitetura lógica

### 1. Research Gateway

- valida `ResearchRequest`;
- autentica projeto/ator;
- aplica política, orçamento, prioridade e freshness;
- gera idempotency key;
- registra `ResearchRun` no Control Plane.

### 2. Research Director

Um agente coordenador global. As especialidades WEB, NEWS, GITHUB, SCIENTIFIC, API, DATASET, VIDEO, BOOK, DOCUMENT, SOURCE VERIFIER, LICENSE, SECURITY, DOWNLOAD, SYNTHESIS e AUDIT permanecem como perfis/workers internos do Research AI, não como dezenas de agentes globais independentes no Control Plane.

### 3. Query Planner

Produz consultas distintas por fonte, idioma, geografia, data, sinônimos, entidades e identifiers. Determina quais fontes primárias devem existir antes de aceitar evidência secundária.

### 4. Discovery Layer

Adaptadores independentes para:

- web/news search;
- GitHub;
- Crossref;
- OpenAlex;
- DataCite;
- Semantic Scholar;
- PubMed/NCBI;
- Europe PMC;
- DOAJ/DOAB/OAPEN;
- arXiv;
- repositórios institucionais;
- YouTube Data API;
- Open Library/Google Books apenas conforme termos;
- CKAN;
- Socrata;
- STAC;
- RSS/Atom;
- portais e APIs oficiais dos domínios dos projetos.

Descoberta e aquisição são separadas: resultado de busca é candidato, não evidência validada.

### 5. Web Acquisition

Dono principal: Crawl4AI.
Browser engine: Playwright, somente quando JS/interação for necessária.

Regras:

- robots/terms/policy por domínio quando aplicável;
- SSRF guard antes de qualquer fetch;
- bloqueio de IPs privados/link-local/metadata endpoints;
- redirects revalidados;
- timeout, tamanho máximo, content-type allowlist;
- HTML sanitizado;
- conteúdo da página tratado como dado não confiável, nunca como instrução do agente.

### 6. Document Acquisition & Parsing

Dono principal: Docling para PDF, DOCX, PPTX, XLSX, HTML, tabelas e estrutura documental.
MarkItDown fica como `REFERENCE/FALLBACK`, ativado somente para MIME/edge case em que benchmark demonstre ganho real; não será segundo parser padrão.

### 7. Download Security Pipeline

`SOURCE_VERIFIED → RIGHTS_CHECK → QUARANTINE → DOWNLOAD → SHA256 → MIME_MAGIC_VALIDATION → ARCHIVE_LIMITS → MALWARE_SCAN → METADATA → IMMUTABLE_RAW_STORAGE → PARSING → DERIVED_STORAGE → HANDOFF`

Nunca executar binário, macro, script ou conteúdo baixado automaticamente.

### 8. API Discovery & Probe Engine

Suporta REST/OpenAPI, GraphQL, WebSocket, MCP, STAC, CKAN/Socrata, FTP/SFTP, RSS/Atom, JSON/XML/CSV/XLSX e bulk downloads.

Para cada API registra provider, official, docs, auth, rate limit, pagination, schema, coverage, update frequency, cost, license/terms, sample request/response, probe date, latency, status e integration recommendation.

Probe real somente quando autorização, termos e credenciais permitem. Segredos nunca entram em logs/packages.

### 9. Dataset Engine

DuckDB é o motor canônico de inspeção local de CSV, Parquet, JSON e arquivos analíticos compatíveis. PyArrow pode ser usado para interoperabilidade de formatos colunares.

O profiler registra grain, rows, columns, types, missingness, duplicates, ranges, cardinality, date coverage, schema drift, size, freshness e known limitations. Não adicionar outro framework de dataframe como dependência central sem necessidade demonstrada.

### 10. GitHub Research Engine

Pesquisa por capacidades, não apenas nomes. Para cada candidato registra atividade, releases, linguagem, licença, arquitetura, dependências, manutenção, componentes úteis, riscos de supply chain e risco comercial.

Classificação final: `USE`, `ADAPT`, `REFERENCE`, `REJECT`.

Antes de `USE/ADAPT`, aplica o Open Source Intake Gate existente da Holding.

### 11. Source/Evidence/Provenance Registry

Entidades centrais:

- `Source`
- `SourceSnapshot`
- `SourceHealthCheck`
- `ResearchRequest`
- `ResearchRun`
- `QueryExecution`
- `DocumentAsset`
- `Claim`
- `Evidence`
- `Contradiction`
- `ApiCandidate`
- `DatasetCandidate`
- `RepositoryCandidate`
- `LicenseAssessment`
- `SecurityAssessment`
- `ResearchPackage`
- `ResearchAudit`

Toda evidência mantém proveniência até a origem e versão/snapshot. Nenhum claim importante pode ficar sem evidence links.

### 12. Temporal Semantics

Separar obrigatoriamente:

- `published_at`
- `effective_at`
- `observed_at`
- `retrieved_at`
- `valid_from`
- `valid_until`
- `source_version`

Isso evita tratar documento recentemente baixado como informação recente.

### 13. Deduplication & Canonicalization

Chaves e fingerprints para canonical URL, SHA-256, DOI, PMID, arXiv ID, ISBN, ORCID, ROR, GitHub owner/repo, dataset IDs e source IDs. Detectar mirrors, versões publicadas vs preprints, forks e republicações.

### 14. Workflow Durability

Temporal é o padrão para runs de pesquisa multi-etapa, retries, timeouts, cancelamento, resume e compensation. Cloud Scheduler permanece responsável somente por iniciar rotinas/watchers de alto nível. Não haverá dois schedulers concorrendo pela mesma responsabilidade.

Se Temporal não for contratado/provisionado, a implantação não deve simular durabilidade com memória local; o run fica bloqueado até o durable executor aprovado estar disponível.

### 15. Storage

Reutilizar infraestrutura GCP da Holding:

- Cloud SQL PostgreSQL 16: registry e estado transacional, em schema/role isolado do Research AI;
- Google Cloud Storage: `quarantine`, `raw-immutable`, `derived`, `research-packages`;
- Secret Manager: credenciais;
- Artifact Registry: imagens;
- Cloud Run: APIs/workers stateless;
- Pub/Sub apenas para eventos de integração entre unidades, como `research.package.ready`, não como segunda orquestração interna.

### 16. Search Provider Policy

Search providers são adaptadores substituíveis. Resultado de search SaaS não é fonte canônica.

Brave Search pode ser usado como discovery transitório, mas seus termos padrão de 2026 proíbem retenção/cache/database de Search Results sem plano que conceda storage rights. Portanto, não persistir payload/resultados Brave no Source Registry sob termos padrão. O License Auditor deve registrar o plano/termos efetivos antes de habilitar persistência.

Tavily/Exa podem ser avaliados como fornecedores alternativos, mas o sistema nunca dependerá de um único search SaaS; fontes oficiais e acquisition direta permanecem obrigatórias para evidência.

### 17. Quality Engine

Score multidimensional separado, nunca um número mágico único:

- authority;
- primary-source status;
- freshness;
- directness;
- independence;
- coverage;
- reproducibility;
- rights clarity;
- technical integrity.

O pacote pode registrar uma síntese de confiança, mas deve preservar os componentes e justificativas.

### 18. Contradiction Engine

Fontes confiáveis que discordam permanecem registradas. O sistema não escolhe silenciosamente uma delas. O package deve mostrar conflito, contexto temporal/metodológico e motivo de eventual preferência.

### 19. Autonomous Watchers

Watchers permitidos para source health, API/schema/docs changes, releases/licenças/CVEs, novos datasets, papers relevantes e alternativas GitHub superiores.

Todo watcher passa pelo `NoveltyRelevanceGate` antes de criar pesquisa. Mesma evidência não gera pacote novo por simples repetição.

### 20. Observabilidade

OpenTelemetry é o padrão de tracing; Prometheus/Cloud Monitoring continuam recebendo métricas. IDs de correlação: `request_id`, `research_run_id`, `source_id`, `asset_id`.

Métricas mínimas: requests, success/failure/partial, sources per run, source diversity, citation coverage, primary-source ratio, freshness, duplicates, API probe success, download rejects, malware/security rejects, license blocks, latency, token cost, search/API cost, retries e handoff success.

## Modelo de autonomia

Research AI pode pesquisar, baixar material permitido e testar endpoints de baixo risco dentro de políticas aprovadas. Não pode aceitar novos termos pagos, executar código remoto, contornar controles de acesso, ampliar credenciais, fazer fork/incorporação de código ou publicar conhecimento canônico sem gates correspondentes.

## Critério de conclusão

Research AI só recebe status `OPERATIONAL` quando todos os cenários do arquivo `E2E_ACCEPTANCE_MATRIX.md` passarem em uma única versão candidata, incluindo integrações reais autorizadas de múltiplos projetos. Teste parcial de um módulo não promove a versão.
