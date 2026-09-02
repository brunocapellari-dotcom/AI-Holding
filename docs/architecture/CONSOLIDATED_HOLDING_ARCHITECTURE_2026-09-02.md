# Arquitetura Consolidada da Holding — 02/09/2026

## Objetivo

Consolidar as rodadas de pesquisa tecnológica e comercial em uma arquitetura única, evitando duplicação de ferramentas e transformando projetos open source em componentes substituíveis. O AI-Holding continua sendo o Control Plane operacional da Holding; este documento não cria uma segunda fonte de verdade.

## Regra principal

A Holding não adota um projeto GitHub inteiro por padrão. Cada repositório é classificado como `CORE`, `COMPONENTE`, `REFERENCIA`, `FUTURO` ou `REJEITADO_POR_REDUNDANCIA`. Sempre que possível, absorver algoritmos, padrões, protocolos e módulos úteis e manter o domínio e os contratos no nosso próprio código.

Todo componente externo passa antes pelo Open Source Intake Gate de segurança, licença, manutenção e estratégia de saída.

## 1. Núcleo compartilhado

### 1.1 Control Plane e Hermes

- `AI-Holding` permanece a fonte operacional canônica para projetos, milestones, acceptance criteria, tarefas, dependências, agentes, runs, decisões, aprovações, incidentes e auditoria.
- Hermes é a interface executiva e coordenador acima do Control Plane.
- `LangGraph`: COMPONENTE para estado/raciocínio de agentes.
- `LiteLLM`: COMPONENTE preferencial para roteamento de modelos e independência de fornecedor.
- `Temporal`: FUTURO para workflows longos e realmente duráveis; não substituir o Task/Run Ledger.
- `Windmill`: COMPONENTE para scripts internos, jobs, APIs e ferramentas operacionais rápidas; nunca fonte canônica de projeto.
- `n8n`: COMPONENTE opcional apenas para integrações SaaS/webhooks simples.
- `Plane`: REJEITADO_POR_REDUNDANCIA como PMO principal. Pode ser avaliado apenas como UI externa se o Control Plane precisar de uma visualização complementar.
- `Goose`, `OpenHands`, `Aider`, Claude Code e Codex: executores/assistentes de engenharia; nenhum recebe autoridade acima do Control Plane.

### 1.2 Business OS

- Frappe/ERPNext será o sistema transacional corporativo para finanças, centros de custo, projetos, compras, vendas e ativos quando implantado.
- Frappe HRMS, CRM, Helpdesk, LMS e Insights são COMPONENTES preferenciais quando evitarem reconstruir funções genéricas.
- O ERP não substitui o AI-Holding e não armazena conhecimento canônico do Segundo Cérebro.
- Separação: ERP = verdade transacional; AI-Holding = governança operacional; Obsidian/Knowledge Core = conhecimento; BigQuery = verdade analítica.
- Fiscal Brasil deve usar adaptadores próprios e bibliotecas especializadas como NFePHP onde tecnicamente e juridicamente adequado; não assumir cobertura fiscal completa do ERPNext.

### 1.3 SaaS Product Core

Padrão compartilhado para novos produtos:

- PostgreSQL/PostGIS para estado transacional e geoespacial quando necessário.
- PWA/web-first; Capacitor quando houver necessidade móvel nativa; Flutter apenas quando PWA/Capacitor não atender.
- MapLibre + deck.gl para mapas.
- OpenMeter para metering/usage billing quando necessário.
- OpenFeature/flagd para feature flags.
- PostHog para product analytics.
- Formbricks para feedback estruturado.
- Frappe Helpdesk/alternativa leve para suporte.
- Caddy como proxy/HTTPS em instalações self-hosted.
- Google Cloud Run/Artifact Registry permanecem válidos no stack atual; Coolify/Forgejo/Harbor/Woodpecker são alternativas de soberania futura, não duplicação imediata.

## 2. Knowledge Factory

Criar uma fábrica contínua e auditada de conhecimento para Hermes, agentes e Obsidian.

### 2.1 Fontes

- oficiais/regulatórias e documentação primária;
- literatura acadêmica e OpenAlex;
- GitHub e documentação técnica;
- datasets públicos autorizados;
- documentos internos;
- vídeo/áudio autorizado;
- transmissões e mídia como sinal apenas quando não forem fonte primária.

### 2.2 Componentes selecionados

- `Docling`: CORE para documentos estruturados/PDF.
- `LlamaIndex`: COMPONENTE code-first para ingestão/RAG e conectores.
- `Graphiti`: COMPONENTE preferencial para grafo temporal de conhecimento.
- `pgvector`: escolha inicial de vetores por reaproveitar PostgreSQL; Qdrant fica FUTURO se escala/latência justificar.
- `Microsoft GraphRAG`: REFERENCIA metodológica para exploração de grandes corpora; não segundo grafo canônico.
- `OpenAlex`: COMPONENTE de descoberta acadêmica.
- `changedetection.io` e RSSHub: COMPONENTES de detecção de mudança/feed quando permitido.
- `whisper.cpp`: COMPONENTE para transcrição local.
- `PySceneDetect`: COMPONENTE para segmentação de vídeo.
- `yt-dlp`: COMPONENTE condicionado a direitos/termos; não é autorização para baixar conteúdo protegido.
- OCR/vision model: componente substituível para slides, gráficos, mapas, código e procedimentos visuais.
- RAGAS/DeepEval/promptfoo: avaliações e gates de competência/segurança.

### 2.3 Agentes funcionais

- Source Hunter: encontra a fonte primária de claims/dados.
- Dataset Scout: procura datasets, avalia licença, qualidade, viés e utilidade.
- Video Scout: descobre conteúdo autorizado/relevante.
- Knowledge Gap Engine: mede lacunas por domínio N0-N6.
- Knowledge Transfer Agent: pergunta onde um novo conhecimento pode melhorar projeto, produto ou receita.
- Official Sources News Engine: produz notícias próprias a partir de fatos oficiais, dados e contexto, preservando evidências e separando fato de inferência.

Instagram, perfis de notícias e portais não são fontes canônicas. Podem servir apenas como descoberta eventual; o sistema deve migrar para a fonte primária sempre que possível.

## 3. Data e Model Core

- BigQuery permanece fonte analítica principal das unidades que já o adotaram.
- `dlt`: ingestão Python incremental quando reduzir código.
- Polars + DuckDB: processamento/backfill/QA local.
- OpenLineage: padrão de lineage quando houver massa crítica.
- OpenMetadata: FUTURO após contracts/lineage/quality justificarem catálogo dedicado.
- MLflow + Feast + Evidently: Model Factory, ativada somente com modelos operacionais validados.
- BentoML: FUTURO para serving dedicado quando Cloud Run/API existente não for suficiente.
- Nixtla/StatsForecast/NeuralForecast, Darts/sktime e PyOD: biblioteca de forecast/anomalia, escolhida por problema e benchmark, não instalada inteira por padrão.
- PM4Py + OR-Tools/Timefold: núcleo de Process/Optimization Intelligence.

## 4. Security Control Plane — inegociável

- identidade: OIDC/IAM; Zitadel é candidato preferencial para multi-tenant B2B self-hosted;
- autorização relacional: OpenFGA;
- policy-as-code: OPA;
- segredos: OpenBao ou Secret Manager conforme ambiente; nunca em prompt, repo ou .env de produção;
- SBOM: Syft;
- vulnerabilidades/misconfig: Trivy; Grype fica complementar;
- segredos em código: Gitleaks;
- SAST: Semgrep;
- assinatura de artefatos: Cosign;
- runtime: Falco e/ou Wazuh conforme camada;
- perímetro web self-hosted: Coraza + CrowdSec quando aplicável;
- telemetria: OpenTelemetry; OpenObserve é candidato self-hosted para logs/traces quando substituir serviços gerenciados fizer sentido;
- isolamento de execução de agentes/código: gVisor/Firecracker apenas quando o risco justificar.

Nenhum agente recebe credencial de produção diretamente. Toda ação de alto impacto passa por identidade, policy, autorização, audit log e limite de autonomia.

## 5. Decisões de consolidação

### Não criar como produto separado agora

- Voice Operations: Shared Engine; pode virar produto futuro.
- GeoRisk/Live Earth: Shared Geo Engine e módulo AgroLog; spin-off só após receita/uso externo.
- Tax Reform Intelligence: módulo do Knowledge & Compliance OS.
- Contract/Document Operations: módulo do Knowledge & Compliance OS.
- Training/SOP: módulo do Knowledge & Compliance OS.
- Road Intelligence: módulo do Fleet OS.
- Tire/Fuel Fraud/Detention/Parts Marketplace: módulos do Fleet OS.
- Traceability/Carbon/Agro Quality: módulos AgroLog no primeiro estágio.
- Agent Security Platform: infraestrutura interna primeiro; produto apenas após maturidade comprovada.
- Data Marketplace/API: canal de monetização transversal, não unidade autônoma inicialmente.

### Não reconstruir funções genéricas

Não criar do zero ERP, CRM, helpdesk, assinatura eletrônica, billing genérico, feature flags, CI básico, mapa base, OCR genérico ou auth quando componente aberto adequado puder ser isolado/substituído.

## 6. Regra de código próprio

Criar código proprietário exatamente onde está o moat:

- modelos de decisão e scores;
- normalização Brasil;
- reconciliação multi-fonte;
- port-call/fila/ETA proprietários;
- Fleet Profitability e custos reais;
- Route/Geo Risk;
- Supply Chain Trace/Passport;
- News/Impact Engine;
- knowledge promotion/audit logic;
- Sports matchup/video features;
- portfolio/risk models;
- optimization/process intelligence;
- autorização/autonomia específica da Holding.

Open source fornece motores e blocos; contratos de domínio, regras, dados derivados e inteligência permanecem nossos.

## 7. Gates de promoção

Qualquer tecnologia ou novo módulo precisa provar:

1. problema real;
2. benefício mensurável;
3. licença compatível;
4. Open Source Intake aprovado;
5. sem duplicação arquitetural;
6. rollback/estratégia de saída;
7. observabilidade;
8. testes automatizados;
9. threat model e controles mínimos;
10. owner e acceptance criteria no AI-Holding.
