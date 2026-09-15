# Research AI — Stack Decisions

Data de corte: 2026-09-15

Classificações: `USE`, `ADAPT`, `REFERENCE`, `REJECT`.

| Capacidade | Escolha | Classificação | Decisão |
|---|---|---:|---|
| Typed AI/agents | `pydantic/pydantic-ai` | USE | Contratos tipados, Python e boa aderência ao stack Pydantic/FastAPI existente. Evita LangChain/LangGraph paralelos. |
| Durable workflows | `temporalio/sdk-python` | USE | Owner único de retry, timeout, resume, cancellation, compensation e long-running runs. Cloud Scheduler fica apenas como trigger. |
| Web crawling | `unclecode/crawl4ai` | USE | Crawler principal; Apache-2.0, ativo e orientado a extração para agentes. |
| Browser automation | `microsoft/playwright` | USE | Browser engine para JS/interaction; não é crawler concorrente. Apache-2.0. |
| Document parsing | `docling-project/docling` | USE | Parser principal para PDF/DOCX/PPTX/XLSX/HTML/tabelas; MIT e ativo. |
| Document conversion | `microsoft/markitdown` | REFERENCE | Só entra como fallback mediante benchmark por MIME/edge case. Não duplicar Docling por padrão. |
| Dataset inspection | `duckdb/duckdb` | USE | SQL analítico embutido, CSV/Parquet/JSON e profiling sem criar serviço de banco adicional. MIT. |
| Columnar interoperability | Apache Arrow / PyArrow | ADAPT | Usar somente quando necessário para formatos colunares e handoff; DuckDB continua dono da análise local. |
| Observability | OpenTelemetry Python | USE | Traces/metrics/log correlation. Prometheus/Cloud Monitoring existentes continuam sinks. |
| Download malware scan | `Cisco-Talos/clamav` | USE-AS-SERVICE | Scanner isolado, nunca incorporar/modificar código GPL no produto proprietário sem nova análise. |
| MIME detection | libmagic | USE | Detectar conteúdo real; extensão nunca é fonte de verdade. |
| Source registry | Cloud SQL PostgreSQL 16 | USE EXISTING | Novo schema/role, não nova instância. JSONB/FTS antes de adicionar search cluster. |
| Raw/derived storage | Google Cloud Storage | USE EXISTING | Buckets separados: quarantine, raw immutable, derived e research packages. |
| Secrets | Google Secret Manager | USE EXISTING | Nenhum vault paralelo. |
| Container registry | Artifact Registry | USE EXISTING | Imagens assinadas/digest pinning. |
| Runtime | Cloud Run | USE EXISTING | API e workers stateless. |
| Cross-project eventing | Pub/Sub | ADAPT | Apenas handoff/event fan-out; não substituir Temporal internamente. |
| Open-source intake | Scorecard + ORT + Syft + Gitleaks + Semgrep + Trivy + Cosign | USE EXISTING | Reutilizar gate já oficial da Holding. |
| General web search | Provider adapter | ADAPT | Provider substituível. Discovery não pode virar dependência canônica de um SaaS. |
| Brave Search | Brave API | REFERENCE/CONDITIONAL | Bom índice independente; termos padrão atuais proíbem retenção/cache de Search Results sem storage rights. Só habilitar conforme contrato/plano. |
| Tavily | Tavily API | REFERENCE | Útil para discovery/AI search; termos e processamento de input/output exigem review por caso de uso. Não é evidência primária. |
| Exa | Exa API | REFERENCE | Forte opção semântica/deep search; avaliar contrato/custo e direitos antes de promoção. |
| Firecrawl | `mendableai/firecrawl` | REJECT CORE | Sobrepõe crawler/browser e licença AGPL do upstream aumenta risco comercial. Pode ser estudado como referência ou SaaS isolado. |
| Elasticsearch/OpenSearch | — | REJECT NOW | Redundante no volume esperado; PostgreSQL JSONB/FTS + object storage primeiro. |
| MinIO | — | REJECT | GCS já resolve object storage gerenciado. |
| Segundo Postgres | — | REJECT | Duplicação operacional. |
| LangChain + LangGraph | — | REJECT CORE | Evitar segunda camada de agentes/orquestração; PydanticAI + Temporal são os owners. |

## Fontes científicas/dados canônicas

### Metadados científicos

- Crossref REST: DOI/publication metadata, funding, license, updates, ORCID/ROR.
- OpenAlex: graph de works/authors/sources/institutions/topics.
- DataCite REST/OAI-PMH: DOI metadata de datasets/software e provenance.
- Semantic Scholar Academic Graph: papers, citations, authors, recommendations e datasets.
- PubMed/NCBI E-utilities: biomédico/saúde.
- Europe PMC: complemento biomédico/open access.
- DOAJ: journals/articles open access.
- DOAB/OAPEN: livros acadêmicos open access.
- arXiv: preprints; nunca confundir preprint com versão peer-reviewed.
- SSRN: metadata/discovery quando apropriado e conforme termos.
- Repositórios institucionais: full text legal e versões autorais.

### Discovery de datasets/APIs

- DataCite.
- CKAN Action API.
- Socrata Open Data APIs.
- STAC API para geoespacial/earth observation.
- Catálogos governamentais e portais oficiais específicos de cada projeto.
- GitHub API para software e releases.
- RSS/Atom para fontes que disponibilizem feeds oficiais.

### Vídeo/livro

- YouTube Data API para metadata/discovery; download somente quando os direitos permitem.
- Open Library para metadata/bulk dumps conforme política de uso; não tratar API gratuita como backend ilimitado.
- Google Books e catálogos editoriais/bibliotecas como fontes complementares de metadata.
- DOAB/OAPEN como prioridade para livros acadêmicos legalmente acessíveis.

## Regra de substituição

Uma ferramenta só substitui outra quando demonstra ganho material em pelo menos um eixo — qualidade, confiabilidade, segurança, licença, custo, performance ou manutenção — sem criar sobreposição operacional injustificada. A comparação deve ser registrada no Source/Component Registry e passar pelo Open Source Intake Gate.
