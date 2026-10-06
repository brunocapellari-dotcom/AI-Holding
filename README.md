# AI Holding — Operating System

Sistema operacional de gestão, decisão, coordenação, execução, segurança e controle dos projetos da Holding Digital.

Este repositório não é protótipo. O PostgreSQL mantém a verdade **operacional** da Holding; GitHub mantém a verdade do software; o Obsidian/Segundo Cérebro permanece um sistema externo e transversal, responsável pelo conhecimento consolidado. A Holding consulta o Segundo Cérebro e envia resultados/evidências para o seu pipeline de validação, mas não promove conhecimento próprio como verdade canônica.

## Cadeia de comando

```text
Owner / Conselho Humano
        ↓
      HERMES
        ↓
Holding Control Plane
        ↓
CEO IA · PMO IA · Governança/Risco/Auditoria · Consultores
        ↓
Unidades / Projetos
        ↓
Agentes e Workers
```

Hermes é a interface executiva persistente do Owner. Ele consolida estado, custos, prioridades, riscos, bloqueios e decisões; transforma ordens em trabalho estruturado e acompanha o trabalho até a conclusão. Hermes é independente do modelo utilizado.

## Stack oficial

- **Agno AgentOS** — runtime principal de agentes, teams, workflows, filas duráveis, scheduler e human-in-the-loop.
- **LiteLLM** — gateway central de modelos, fallback, budgets e custos por projeto/agente.
- **OpenHands** — camada operacional de coding agents e workspaces isolados.
- **Claude Code / Codex** — workers especializados de engenharia; não são a Holding.
- **GitHub** — fonte canônica de código, branches, commits, PRs, issues técnicas e CI/CD.
- **Docker MCP Gateway** — fronteira padrão de ferramentas/MCPs; acesso não é concedido por prompt.
- **Infisical** — destino oficial para segredos e identidades de máquina; Secret Manager permanece apenas durante a migração controlada.
- **Docker + E2B/microVM** — isolamento de execução conforme o risco.
- **Langfuse** — observabilidade central de IA.
- **PostgreSQL** — persistência operacional da Holding, sem substituir o Segundo Cérebro.

Não serão introduzidos em paralelo ADK, Microsoft Agent Framework, LangGraph, CrewAI, AutoGen ou outro runtime equivalente sem necessidade comprovada. Temporal e OpenFGA são reservas condicionais.

## Princípios não negociáveis

- **Sem percentuais subjetivos.** Progresso deriva de acceptance criteria verificados e ponderados.
- **Sem estado operacional escondido em chat.** O PostgreSQL é a fonte operacional de verdade.
- **Sem conhecimento canônico na Holding.** Conhecimento consolidado pertence ao Segundo Cérebro.
- **Sem bloqueio silencioso.** Exceções viram incidentes, tarefas bloqueadas ou decisões.
- **Sem autonomia irrestrita.** A0–A6 expressa autonomia decisória; autorização técnica continua explícita e mínima.
- **Sem acoplamento a um modelo.** O acesso a modelos passa pelo gateway.
- **Segurança fora do prompt.** Intenção, autorização, credencial, execução e auditoria são camadas distintas.
- **Toda alteração relevante é auditável.** Mutações carregam ator e request ID.
- **Execução idempotente e isolada.** Trabalho repetido não duplica efeitos; código de maior risco executa em sandbox.
- **Produção observável.** Health, readiness, métricas, traces, custos, CI e evidências fazem parte da entrega.

## Domínios operacionais preservados

1. Project Registry
2. Milestones e Acceptance Criteria
3. Task Ledger e dependências
4. Agent Registry
5. Run Ledger
6. Decision Queue — “Precisa de você”
7. Approvals
8. Incident Manager
9. Policy Engine A0–A6
10. Audit Log
11. Executive Summary e progresso objetivo

## Fronteiras do repositório

A migração é incremental e não descarta o Control Plane já validado. O pacote histórico `app/` permanece como núcleo de domínio durante o strangler migration; as novas fronteiras passam a ser explicitadas em `apps/`, `services/`, `agents/`, `workflows/`, `integrations/`, `security/`, `infrastructure/`, `projects/` e `docs/`.

A arquitetura oficial e o mapa de migração estão em `docs/architecture/holding-os.md` e `docs/architecture/migration-plan.md`.

## Organização dos projetos

A Holding referencia as unidades, mas não copia o código delas. AgroLog MT mantém no mesmo repositório os domínios agrícola/logístico, Inteligência Pecuária e Maritime Intelligence; o Control Plane pode administrá-los como projetos/subprojetos lógicos independentes.
