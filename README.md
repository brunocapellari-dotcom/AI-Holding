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

## Arquitetura-alvo

- Cloud Run: API privada do Control Plane
- Cloud SQL PostgreSQL: estado operacional
- Secret Manager: credenciais
- Artifact Registry: imagens de produção
- Cloud Logging/Monitoring: telemetria
- Google Cloud Build: qualidade, provenance, promoção e entrega controlada
- GitHub Actions: diagnóstico manual legado, sem autoridade de produção
- BigQuery: dados analíticos das unidades; não substitui o PostgreSQL operacional
- Hermes + Llama: Assistente Executivo, acima do Control Plane

## Organização dos projetos

A Holding é independente dos repositórios das unidades. O Control Plane referencia cada unidade pelo campo `repository` e por metadados, sem copiar seu código.

AgroLog MT mantém no mesmo repositório os domínios agrícola/logístico, **Inteligência Pecuária** e **Maritime Intelligence**, com fronteiras internas próprias. O Control Plane continua enxergando cada domínio que precise gestão separada como projeto ou subprojeto lógico.
