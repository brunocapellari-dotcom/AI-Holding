# Hermes AI Platform — Especificação Canônica e Gap Analysis

Data de corte: 2026-09-15
Status: PROPOSTO PARA INCORPORAÇÃO AO CONTROL PLANE
Owner: Owner / Holding Digital

## 1. Missão

Construir a plataforma central de inteligência artificial compartilhada por todo o ecossistema. Hermes evolui de assistente executivo para AI Chief of Staff, AI Orchestrator, AI Architect, AI Knowledge Interpreter, AI Research Coordinator, AI Agent Factory, AI Skill Factory, AI Project Commander e AI Decision Support System.

O Owner informa o objetivo. Hermes determina projeto, agente, skill, modelo, ferramenta, contexto, conhecimento, workflow e política corretos.

## 2. Fronteiras obrigatórias

- Hermes AI Platform: inteligência, interpretação, orquestração, roteamento e execução controlada.
- AI-Holding: Control Plane, governança, portfólio, autoridade, approvals, incidentes, auditoria e estado operacional canônico.
- Segundo Cérebro: conhecimento institucional, proveniência, claims, evidências, histórico e conhecimento estrutural.
- Research AI: pesquisa, descoberta, coleta, verificação, licença e security intake de fontes externas.
- Projetos: execução especializada de domínio.

Hermes não substitui o Control Plane, o Segundo Cérebro, o Research AI nem a lógica interna de cada projeto.

## 3. Estado auditado em 2026-09-15

### EXISTE

- AI-Holding Control Plane em FastAPI/PostgreSQL com Project Registry, Task/Run Ledger, decisões, approvals, incidentes, auditabilidade e idempotência.
- Hermes cadastrado como AgentSeed no AI-Holding.
- Arquitetura consolidada já define Hermes acima do Control Plane.
- LangGraph selecionado como componente de estado/raciocínio.
- LiteLLM selecionado como gateway preferencial de modelos.
- Temporal já classificado como mecanismo futuro para workflows duráveis.
- Graphiti selecionado como componente preferencial de grafo temporal.
- pgvector como escolha vetorial inicial.
- OPA/OpenFGA/OIDC, OpenTelemetry e gates de segurança/licença já definidos na arquitetura da Holding.
- Política de não acoplamento a provedor/modelo e autonomia A0-A6 já existem.

### PARCIAL

- Hermes atual possui apenas executive-reporting, decision-queue e portfolio-observation; não implementa o Cognitive Core proposto.
- Agent Registry existe no Control Plane, mas não há Agent Factory completa com geração, sandbox, eval, security review, promotion e retirement automatizados.
- Knowledge Factory e Segundo Cérebro existem arquiteturalmente, porém o contrato de recuperação seletiva Hermes -> Knowledge ainda precisa ser formalizado.
- Observabilidade existe para o Control Plane, mas ainda não há tracing padronizado de request -> project -> agent -> skill -> model -> tool -> cost.
- Segurança existe como arquitetura da Holding, mas falta enforcement próprio do Hermes Tool Gateway.

### FALTA

- Repositório próprio e serviço independente Hermes AI Platform.
- AI Core compartilhado.
- Intent Engine, Goal Engine, Task Graph Planner, Project/Agent/Model/Context Routers.
- Knowledge Interpreter, Knowledge Gap Detector e Research Orchestrator.
- Cross Project Relation Engine.
- World State operacional.
- Model Registry e Model Evaluation Lab específicos do ecossistema.
- Local Model Service com hardware discovery.
- Capability Registry e Project Adapter padronizado.
- Tool Gateway/MCP central com Policy Engine obrigatório antes de cada ação.
- Skill Factory versionada.
- Self-Improvement Controlled Loop com sandbox, A/B, auditor independente e rollback.
- Proactive Hermes / Daily Executive Brief.
- Scenario, Hypothesis e Confidence Engines.
- Golden Tasks e Security Test Lab dedicados.
- SDK/API comum do Hermes.
- Control Center do Hermes.

## 4. Gap Analysis prioritário

| gap_id | descrição | impacto | prioridade | dependências | solução | teste | risco | status |
|---|---|---|---|---|---|---|---|---|
| HERMES-001 | Repositório/serviço Hermes separado inexistente | crítico | P0 | GitHub/deploy target | criar serviço próprio mantendo AI-Holding como Control Plane | CI + health + contract test | médio | OPEN |
| HERMES-002 | Cognitive Core inexistente | crítico | P0 | HERMES-001 | implementar engines e routers por contratos próprios | Golden Tasks | alto | OPEN |
| HERMES-003 | AI Core/model gateway não operacional como serviço compartilhado | crítico | P0 | secrets/network | benchmark LiteLLM e implementar adapter estável | provider/fallback/cost E2E | médio | OPEN |
| HERMES-004 | Local Model Service inexistente | alto | P0 | hardware discovery | runtime selecionado por benchmark entre vLLM/SGLang/llama.cpp/Ollama/TensorRT-LLM | local-only Golden Task | médio | OPEN |
| HERMES-005 | Project Router/Capability Registry inexistente | crítico | P0 | project adapters | capability-first routing com health/status/execute contracts | cross-project routing E2E | médio | OPEN |
| HERMES-006 | Knowledge Interpreter e temporal retrieval incompletos | crítico | P0 | Segundo Cérebro/Graphiti | retrieval seletivo com status e temporalidade | historical/contradiction tests | alto | OPEN |
| HERMES-007 | Research handoff automático inexistente | alto | P0 | Research AI contract | Knowledge Gap -> RESEARCH_REQUEST -> package -> Knowledge Factory -> resume | end-to-end gap test | médio | OPEN |
| HERMES-008 | Agent/Skill Factory incompletas | alto | P1 | sandbox/evals/security | factories com registry, permissions, benchmark e promotion gate | create/retire/rollback tests | alto | OPEN |
| HERMES-009 | Tool Gateway policy enforcement inexistente | crítico | P0 | OPA/OpenFGA/identity/secrets | AI request -> policy -> auth -> scoped credential -> execution -> audit | prompt injection/security tests | alto | OPEN |
| HERMES-010 | Long-running missions não possuem engine durável Hermes | alto | P1 | Temporal + Task/Run Ledger | Temporal como executor durável sem substituir ledger canônico | restart/retry/idempotency E2E | médio | OPEN |
| HERMES-011 | Observabilidade/FinOps ponta a ponta incompletas | alto | P1 | OTel/model gateway | trace IDs e custos por projeto/agent/model/tool | trace completeness + cost reconciliation | baixo | OPEN |
| HERMES-012 | Self-improvement sem promotion gate automatizado | alto | P1 | eval lab/auditor | CURRENT -> PROPOSED -> SANDBOX -> TEST -> A/B -> AUDITOR -> PROMOTE/REJECT | regression/rollback test | alto | OPEN |
| HERMES-013 | Cross-project intelligence inexistente | médio | P1 | knowledge/event bus | relation engine baseado em claims/capabilities, não heurística livre | curated transfer cases | médio | OPEN |
| HERMES-014 | Golden Tasks/Security Lab inexistentes | crítico | P0 | services above | suíte canônica obrigatória em CI | 100% pass gate | baixo | OPEN |

## 5. Decisões arquiteturais consolidadas

### 5.1 Control Plane

AI-Holding continua fonte operacional canônica. Não adotar Agno AgentOS, LangSmith, Plane, Jira ou outro produto como segundo Control Plane. Frameworks externos podem ser runners, adapters, UIs ou referências desde que não criem nova verdade operacional.

### 5.2 Model Gateway

LiteLLM permanece candidato preferencial, mas deve passar por benchmark interno. Hermes deve falar com um contrato ModelGateway próprio; LiteLLM é implementação substituível. Nenhum projeto integra diretamente todos os providers quando o AI Core estiver disponível.

### 5.3 Orquestração de agentes

LangGraph permanece candidato principal para grafos cognitivos e checkpointing quando isso simplificar o Cognitive Core. Temporal é o mecanismo preferencial para execução realmente longa/durável, retries e retomadas; o Task/Run Ledger do AI-Holding continua canônico para governança e auditoria.

### 5.4 Conhecimento

Graphiti permanece candidato preferencial para relações temporais e histórico de claims. PostgreSQL/pgvector continua o vetor inicial para reduzir tool-sprawl. Qdrant só entra se benchmark de escala/latência justificar.

### 5.5 Observabilidade

OpenTelemetry é o padrão de instrumentação. Langfuse pode ser usado como camada de LLM/agent observability e eval quando agregar valor sem duplicar o backend existente. Features Enterprise/licenças devem permanecer fora do caminho crítico até justificativa comercial.

### 5.6 Secrets

Manter interface SecretsProvider. Avaliar OpenBao, Google Secret Manager e Infisical de acordo com ambiente e capacidade necessária. Não entregar secrets brutos aos modelos. Credenciais devem ser curtas, escopadas e mediadas pelo Tool Gateway/Policy Engine.

### 5.7 MCP/Tool Gateway

Docker MCP Gateway é candidato forte para isolamento e descoberta de ferramentas, mas não substitui o Policy Engine do Hermes. Toda chamada deve passar por autorização externa ao modelo, timeout, rate limit, audit e egress policy.

### 5.8 AgentOS/Agno

Classificar como COMPONENTE/REFERÊNCIA a benchmarkar, não CORE por padrão. O runtime e seus padrões podem ser úteis para adapters e APIs de agentes; o Control Plane e Agent Registry da Holding permanecem canônicos. Evitar duplicação de memória, governance e observability.

## 6. Local inference — política

Nenhum runtime é padrão universal.

- vLLM: candidato de produção para GPUs e alto throughput.
- SGLang: candidato de produção para workloads de serving/structured generation após benchmark.
- llama.cpp: candidato prioritário para CPU, edge, GGUF e hardware heterogêneo.
- Ollama: candidato de DX/local workstation; não assumir como serving principal sem benchmark.
- TensorRT-LLM: candidato quando hardware NVIDIA e otimização específica justificarem complexidade.

Hardware Discovery deve detectar CPU, RAM, GPU, VRAM, CUDA/ROCm, storage e OS e gerar configuração compatível. Nenhum modelo deve ser executado apenas porque é popular.

## 7. Model policy

Llama é família prioritária inicial, não dependência permanente. O Model Evaluation Lab deve comparar continuamente open e closed models por classes FAST, CHEAP, ROUTINE, PRIVATE, OFFLINE, REASONING, DEEP_REASONING, RESEARCH, CODING, LONG_CONTEXT, VISION, AUDIO, STRUCTURED_OUTPUT, AUDIT e CRITICAL_REVIEW.

O router registra motivo, versão, custo, latência, qualidade e resultado; fallback e circuit breaker são obrigatórios.

## 8. Contratos mínimos

### ProjectAdapter

- health()
- status()
- capabilities()
- query()
- execute()
- search()
- alerts()

### Mission

- mission_id
- task_id
- dependencies
- project
- agent
- skill
- tool
- model_policy
- input
- expected_output
- status
- retry_policy
- checkpoint
- risk_class
- approval_requirement

### Tool

- tool_id
- owner
- project
- permissions
- risk_level
- input_schema
- output_schema
- timeout
- rate_limit
- audit_level
- allowed_egress

## 9. Segurança inegociável

SYSTEM POLICY, TRUSTED CONTEXT e UNTRUSTED CONTENT são domínios distintos. Web, WhatsApp, PDF, email, GitHub, vídeos, imagens, áudio e transcrições são dados não confiáveis por padrão.

O modelo não autoriza a si mesmo. A cadeia obrigatória é AI -> TOOL REQUEST -> POLICY ENGINE -> AUTHORIZATION -> SCOPED CREDENTIAL -> EXECUTION -> AUDIT.

Novo agente nasce com read mínimo, write=false, external_actions=false, secrets=none, money=false e production_admin=false.

## 10. Golden Tasks obrigatórias

1. Como está a Holding?
2. Continue o AgroLog.
3. Veja o que o Obsidian aprendeu.
4. Isso serve para outro projeto?
5. Pesquise APIs melhores.
6. Crie o agente necessário.
7. Tem agentes duplicados?
8. Use apenas IA local.
9. Transforme isso em vídeo.
10. Monta meu próximo bloco.
11. Esse documento tenta manipular a IA?

## 11. Ordem de implementação aprovada

A ordem lógica permanece:

Audit existing -> Gap Analysis -> external technology/license/security audit -> final architecture -> AI Core -> Local Model Service -> Cognitive Core -> Segundo Cérebro integration -> Research AI integration -> Project Router -> Agent Factory -> Skill Factory -> Holding integration -> remaining projects -> Golden Tasks -> Security Test Lab -> full E2E -> documentation.

Implementação deve avançar autonomamente enquanto reversível e dentro das políticas. Credencial essencial, gasto relevante, dinheiro real, contrato, decisão jurídica, risco crítico, ação irreversível ou dado exclusivo do Owner exigem parada/aprovação.

## 12. Critério de operacionalidade

Hermes só é considerado operacional quando AI Core, modelo local, providers externos, Model Router, fallback, Context Router, Segundo Cérebro, Research AI, Project Router, Agent/Skill Factories, Agent Registry, Cross Project Intelligence, durable missions, security, observability, FinOps, Golden Tasks e E2E funcionarem conjuntamente e os testes de segurança passarem.

Potência cognitiva não concede autoridade irrestrita.
