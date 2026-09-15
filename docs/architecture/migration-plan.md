# Migração para Holding OS

Estratégia: **strangler migration**, sem reescrita total e sem descarte de garantias já validadas.

## Auditoria do estado atual

### Preservar
- FastAPI Control Plane e contratos de domínio.
- PostgreSQL operacional: projetos, milestones, critérios, tarefas, dependências, agentes, runs, decisões, aprovações, incidentes e auditoria.
- Policy Engine A0–A6 e autorização por identidade.
- idempotência e proteção contra runs concorrentes.
- CI com lint, format, typing estrito, dependency audit, Bandit, migrations, cobertura, Terraform, SBOM e Trivy.
- Cloud SQL privado, WIF, Cloud Run autenticado, imagens imutáveis, Secret Manager durante transição.
- critérios objetivos de progresso e filas de decisão/incidente.

### Corrigir
1. O `Universal Knowledge Core` assumiu função canônica do Segundo Cérebro.
2. `Knowledge IA` foi transformado em runtime autônomo dentro da Holding.
3. Cloud Scheduler passou a atuar como scheduler principal de workers, sobrepondo o AgentOS desejado.
4. Hermes ainda não possui fronteira de aplicação própria.
5. Não existe gateway central de modelos/custos.
6. Coding agents não têm serviço operacional isolado.
7. Ferramentas externas ainda não possuem uma fronteira MCP única.
8. Segredos ainda dependem de Secret Manager em vez de Infisical.
9. Observabilidade de IA ainda não está centralizada no Langfuse.

## Fases

### Fase A — contenção e recuperação do deploy
- proibir novas promoções de conhecimento interno para `canonical`;
- redirecionar exportações para uma inbox de validação do Segundo Cérebro;
- manter tabelas legadas para compatibilidade e migração, sem exclusão;
- impedir criação/ativação de schedulers legados por padrão;
- remover a Knowledge IA do acceptance gate obrigatório da Holding;
- manter PMO worker existente como fallback enquanto AgentOS assume o runtime.

Critério de saída: CI verde e deploy de produção não depende de `cloudscheduler.jobs.create`.

### Fase B — fronteiras do monorepo
- `apps/hermes`: interface executiva e contratos Owner ↔ Holding;
- `apps/control_plane`: composição da API e compatibilidade com o núcleo histórico `app/`;
- `services/agent_runtime`: AgentOS;
- `services/model_gateway`: LiteLLM;
- `services/coding_agents`: OpenHands/Claude Code/Codex;
- `services/observability`: Langfuse;
- `services/policy`: política/autorização;
- `services/secrets`: Infisical e ponte temporária Secret Manager;
- `integrations/second_brain`: troca de contexto/evidência;
- `security`: tool gateway, sandbox e threat model;
- `agents`: papéis executivos e agentes de projeto;
- `workflows`: processos duráveis;
- `projects`: manifestos lógicos de unidades.

### Fase C — AgentOS em produção
- montar o FastAPI existente via `base_app` e preservar as rotas existentes em conflitos;
- usar PostgreSQL em schema separado do domínio;
- habilitar scheduler e fila durável do AgentOS;
- autenticar as rotas de runtime antes de liberar execução;
- registrar CEO, PMO, Governança/Auditoria e workflows somente depois de o gateway de modelos estar protegido.

Critério de saída: uma tarefa real percorre Control Plane → AgentOS → worker → evidência → Control Plane sem Cloud Scheduler como orquestrador principal.

### Fase D — modelos, custos e observabilidade
- subir LiteLLM com PostgreSQL e chaves virtuais/budgets;
- rotear modelos por aliases lógicos;
- integrar Langfuse ao gateway/runtime;
- registrar custos por projeto/agente/tarefa;
- Hermes passa a mostrar custo e orçamento do portfólio.

### Fase E — coding agents
- implantar OpenHands Agent Server/Workspace;
- criar contratos de tarefa de engenharia;
- executar Claude Code/Codex em workspace isolado;
- exigir branch, testes, PR e CI;
- merge continua governado por política.

### Fase F — tool gateway e segredos
- Docker MCP Gateway como único caminho padrão para MCPs externos;
- Infisical machine identities por serviço/projeto;
- migrar segredos gradualmente, com verificação antes de retirar Secret Manager;
- usar E2B/microVM para código de risco elevado.

## Estado legado de conhecimento

`knowledge_claims` e `knowledge_outcomes` não serão descartadas nesta migração. Elas passam a representar **candidatos/evidências de transferência**, não a fonte canônica. O valor `canonical` permanece apenas para leitura de histórico até a migração dos registros existentes.

## Bloqueios que exigem Owner

Somente quando chegarmos a uma integração que exija contratação, criação de conta, credencial externa ou gasto material — por exemplo, Infisical Cloud, Langfuse Cloud ou E2B pago — o fluxo deve parar no ponto exato. Até lá, arquitetura, código, testes, configs, self-hosting e migração não destrutiva prosseguem autonomamente.
