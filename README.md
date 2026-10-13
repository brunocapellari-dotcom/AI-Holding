# AI Holding — Control Plane

Fonte operacional de verdade da Holding Digital.

Este repositório não é protótipo. Ele contém o núcleo definitivo para registrar e governar projetos, milestones, critérios objetivos de conclusão, tarefas, dependências, agentes, execuções, decisões humanas, aprovações, incidentes e auditoria.

## Princípios não negociáveis

- **Sem percentuais subjetivos.** Progresso é calculado a partir de acceptance criteria verificados e ponderados.
- **Sem estado escondido em chat.** O PostgreSQL contém o estado operacional canônico.
- **Sem bloqueio silencioso.** Exceções entram como incidentes, tarefas bloqueadas ou decisões.
- **Sem autonomia irrestrita.** Projetos e agentes carregam limites A0–A6; políticas externas podem reduzir, nunca ampliar, esses limites.
- **Sem acoplamento a um modelo.** Hermes, Llama, GPT, Claude e Codex consomem o Control Plane por interfaces estáveis.
- **Toda alteração relevante é auditável.** Mutação de estado gera AuditEvent com ator e request ID.
- **Idempotência em execução.** Tarefas recebem chave idempotente para evitar duplicação.
- **Produção observável.** Health, readiness, métricas, logs e CI fazem parte da base.

## Domínios do núcleo

1. Project Registry
2. Milestones
3. Acceptance Criteria
4. Task Ledger e dependências
5. Agent Registry
6. Run Ledger
7. Decision Queue — “Precisa de você”
8. Approvals
9. Incident Manager
10. Audit Log
11. Executive Summary e progresso objetivo

## Runtime oficial

O caminho padrão de GO-LIVE é **local e sem infraestrutura cloud obrigatória**:

- Docker Compose executa PostgreSQL, API, PMO worker e Knowledge worker.
- A interface do proprietário fica em `http://localhost:8080/`.
- A porta da API é vinculada apenas a `127.0.0.1`; o PostgreSQL não é exposto ao host.
- O bootstrap canônico e as migrações são aplicados antes da API iniciar.
- PMO e Knowledge executam as rotinas existentes pelo mesmo ledger do Control Plane.
- Hermes integra por eventos; não existe um segundo scheduler concorrente dentro da Holding.

Para iniciar o runtime local, use `bash scripts/local_go_live.sh` em shell compatível ou `./scripts/local_go_live.ps1` no PowerShell. Os scripts sobem o Compose, aguardam readiness e mostram o estado dos serviços. O estado persiste no volume `postgres_data`.

O deploy Google Cloud permanece disponível como opção futura, mas é **opt-in**. O job de produção só pode executar quando a variável de repositório `ENABLE_PAID_GCP_DEPLOY` estiver explicitamente definida como `true`. A configuração padrão não cria nem atualiza infraestrutura paga.

## Arquitetura opcional gerenciada

Quando houver decisão humana explícita para usar infraestrutura paga, a configuração existente suporta Cloud Run, Cloud SQL PostgreSQL, Secret Manager, Artifact Registry e Cloud Logging/Monitoring. BigQuery continua reservado a dados analíticos das unidades e não substitui o PostgreSQL operacional.

## Organização dos projetos

A Holding é independente dos repositórios das unidades. O Control Plane referencia cada unidade pelo campo `repository` e por metadados, sem copiar seu código.

AgroLog MT mantém no mesmo repositório os domínios agrícola/logístico, **Inteligência Pecuária** e **Maritime Intelligence**, com fronteiras internas próprias. O Control Plane continua enxergando cada domínio que precise gestão separada como projeto ou subprojeto lógico.
