# Holding Digital / AI Operating System — Especificação Oficial e Gap Analysis

Data: 2026-09-15
Status: CANÔNICO
Escopo: `AI-Holding` / Holding Control Plane

## 1. Missão e fronteira arquitetural

A Holding Digital é o sistema central de gestão, governança, priorização, coordenação, PMO, controle de execução, risco, segurança, finanças, alocação de recursos, avaliação de projetos, Venture Factory e auditoria do ecossistema.

Separação obrigatória:

- **Holding**: administra, governa, prioriza, controla e mede.
- **Hermes AI Platform**: pensa, interpreta, conversa, orquestra e fornece IA compartilhada.
- **Segundo Cérebro**: sabe, aprende, relaciona e preserva conhecimento.
- **Research AI**: pesquisa, descobre, testa, baixa e entrega fontes.
- **Projetos**: executam funções especializadas.

A Holding DB é fonte de verdade **operacional**. Ela não deve ser fonte de verdade de conhecimento institucional duradouro.

## 2. Princípios obrigatórios

1. Mirar versão final e operacional.
2. Auditar antes de reconstruir.
3. Preservar componentes funcionais.
4. Evitar frameworks, agents, bancos e ferramentas redundantes.
5. Não inferir estado por conversa.
6. `COMPLETED` exige evidência objetiva verificável.
7. Planner/Builder não pode ser o único Auditor.
8. Autonomia A0–A6 não implica autoridade irrestrita.
9. Ações críticas, irreversíveis ou de capital material exigem policy gate/human approval.
10. Toda nova ferramenta deve passar por ADOPT/REPLACE/BENCHMARK/RESERVE/REJECT.

## 3. Auditoria do repositório atual

Classificação usada: EXISTE, PARCIAL, FALTA, QUEBRADO, DUPLICADO, OBSOLETO.

| Domínio | Estado | Evidência atual / observação | Ação |
|---|---|---|---|
| Backend / Control Plane | EXISTE | FastAPI + SQLAlchemy + PostgreSQL/Alembic | Preservar e expandir |
| Database operacional | EXISTE | modelos, migrações e estado persistente | Preservar |
| API | EXISTE | projetos, tarefas, runs, decisões, policy, PMO, incidents, agents, executive | Preservar e versionar contratos |
| Project Registry | PARCIAL | projeto, prioridade, autonomia, repo, owner agent e metadata existem | Migrar para contrato oficial completo |
| Estados operacionais | OBSOLETO | enums atuais diferem do contrato oficial | Criar migração compatível e preservar histórico |
| Milestones / Acceptance Criteria | EXISTE | critérios objetivos e evidência persistida | Preservar; usar pelo Auditor |
| Task Ledger | EXISTE | tarefas, idempotência, dependências e runs | Preservar |
| PMO AI | PARCIAL | serviço/worker existe e resolve dependências de tarefas | Expandir para roadmap cross-project e dependency graph global |
| Governance / Policy | PARCIAL | policy determinística e human approval para risco/financeiro/irreversível | Formalizar policies e matriz A0–A6 |
| Audit Log | EXISTE | `AuditEvent` persistente | Preservar e ampliar cobertura |
| Auditor AI | PARCIAL | acceptance criteria e auditoria existem como infraestrutura | Criar auditor independente explícito por entrega/release |
| CEO AI | PARCIAL | arquitetura/agents seedados, mas priorização evidencial completa não verificada | Implementar score/decision evidence |
| Risk AI / Risk Registry | FALTA | existe `RiskLevel`, mas não Registry com probabilidade, impacto, mitigação, owner e revisão | Implementar modelo, API, serviço e testes |
| Security AI | PARCIAL | segurança forte em CI/infra/policies, mas agente/estado consolidado não verificado | Criar security posture + findings registry |
| Architect AI | PARCIAL | decisões arquiteturais/documentação existem | Implementar tool-sprawl registry e gates |
| Finance AI / FinOps | FALTA | não identificado modelo/API operacional de custos, receita, runway, budget, payback e trend | Implementar ledger + collectors + APIs |
| Resource Allocation AI | FALTA | não identificado mecanismo operacional | Implementar recursos, capacidade, orçamento e decisão |
| Venture Factory | PARCIAL | documentação e projeto incubado existem | Transformar em pipeline executável com gates |
| Project Health | FALTA | `/health` atual mede serviço, não saúde consolidada de cada projeto | Implementar engine persistente e API |
| Collector Registry | FALTA | não identificado registry operacional dos collectors | Implementar registry, executions, freshness e retries |
| Collectors externos | FALTA/PARCIAL | workers internos existem; não há cobertura operacional completa para GitHub, CI/CD, AgentOS, DBs, queues, deploys, logs, Langfuse, Hermes, Research, Segundo Cérebro, custos | Criar adapters idempotentes |
| Dependency Graph | PARCIAL | task dependencies existem | Criar grafo PROJECT/SERVICE/DATA/API/AGENT/SKILL/MODEL/INFRASTRUCTURE |
| Hermes integration | PARCIAL | arquitetura prevê interfaces estáveis, integração runtime completa não verificada | Criar adapter/contract versionado |
| Research AI integration | PARCIAL | contratos/documentos existem | Conectar requests/status/cost/findings/failures via adapter |
| Segundo Cérebro integration | PARCIAL / BOUNDARY CONFLICT | repo contém `Universal Knowledge Core`; nova arquitetura exige Segundo Cérebro separado | Migrar para adapter sem perda de provenance |
| AgentOS / Agno | PARCIAL/NÃO VERIFICADO | não identificado como runtime central no código auditado | Benchmark antes de adotar |
| LiteLLM integration | FALTA/NÃO VERIFICADO | não identificado no runtime da Holding | Consumir via Hermes; não duplicar Model Router |
| Auth / Identity | PARCIAL | google-auth, WIF e hardening existentes | Consolidar RBAC/service identities/policy enforcement |
| Secrets | PARCIAL | arquitetura/infra usa Secret Manager; Infisical/OpenBao pode ser avaliado | Não criar segundo vault sem benefício comprovado |
| Observabilidade | PARCIAL | Prometheus/logging/health presentes | Consolidar logs/traces/metrics/cost/security events |
| CI/CD | EXISTE | GitHub Actions, lint, typing, tests, audits e deploy foundation | Preservar e ampliar supply-chain gates |
| Supply-chain security | PARCIAL | ferramentas definidas e parte do pipeline implementada | Confirmar SBOM, signing, license e container scanning em execução |
| Security Test Lab | FALTA/PARCIAL | hardening existe, mas suíte consolidada não identificada | Criar testes de injection/auth/SSRF/XSS/etc. |
| Backups / restore tests | NÃO VERIFICADO | infraestrutura existe, mas restore E2E não foi confirmado nesta auditoria | Tornar restore test obrigatório |
| Frontend | FALTA | nenhum frontend dedicado identificado | Criar apenas se agregar valor; API/Hermes continua interface principal |
| E2E Holding | PARCIAL | E2Es específicos existem, matriz oficial nova ainda não implementada | Implementar os 8 cenários oficiais + acceptance gate |

## 4. Mudanças canônicas no Project Registry

O contrato alvo de projeto passa a incluir, diretamente ou via tabelas relacionadas:

- `project_id`
- `name`
- `mission`
- `repository`
- `status`
- `priority`
- `autonomy_level`
- `owner_agent`
- `knowledge_namespace`
- `capabilities`
- `agents`
- `skills`
- `sources`
- `collectors`
- `models`
- `databases`
- `APIs`
- `dependencies`
- `security_level`
- `budget`
- `current_phase`
- `tasks`
- `blockers`
- `risks`
- `KPIs`
- `last_execution`
- `last_success`
- `last_failure`
- `next_actions`

Evitar transformar o registro em JSON monolítico. Campos com cardinalidade, histórico ou governança próprios devem ficar normalizados.

## 5. Estados operacionais oficiais

Estados oficiais:

- PLANNED
- READY
- RUNNING
- COMPLETED
- FAILED
- BLOCKED
- PAUSED
- CANCELLED

Migração obrigatória:

- não converter cegamente `active`, `incubating`, `archived`, `review` ou `done`;
- registrar tabela de equivalência e migration decision;
- preservar o valor legado quando necessário em metadata/audit;
- nenhum registro pode virar `COMPLETED` sem acceptance evidence.

## 6. Project Contract

Cada projeto deve expor diretamente ou por adapter:

```text
project.health()
project.status()
project.capabilities()
project.tasks()
project.blockers()
project.cost()
project.security()
project.data_health()
project.alerts()
```

Adapters devem ser versionados, timeout-aware, retry-safe, idempotentes quando houver mutação e com circuit breaker quando aplicável.

## 7. Project Health Engine

Estados:

- HEALTHY
- DEGRADED
- AT_RISK
- BLOCKED
- OFFLINE

Inputs mínimos:

- code/repository health
- tests
- deploy
- collectors
- data freshness
- queues
- agents
- errors/incidents
- security
- costs/budget
- dependencies
- knowledge freshness quando aplicável

O score nunca deve esconder causa. Toda classificação precisa expor `reasons`, `evidence`, `freshness` e `confidence`.

## 8. Collector Registry

Modelo mínimo:

```text
collector_id
project_id
source
data_type
frequency
last_success
last_failure
freshness
latency
retry_policy
status
```

Adicionar executions/history separados para evitar sobrescrever evidência histórica.

Collectors prioritários:

1. GitHub/repositories/commits/PRs/issues.
2. GitHub Actions/CI-CD.
3. deploy/runtime.
4. databases.
5. queues/workers/scheduler.
6. logs/metrics/traces.
7. Langfuse/LLM observability quando usado.
8. Hermes AI Platform.
9. Research AI.
10. Segundo Cérebro.
11. project APIs/contracts.
12. model/API/cloud/software costs.

## 9. Risk Registry

Campos oficiais:

```text
risk_id
project_id
description
probability
impact
severity
mitigation
owner
status
date_detected
last_review
```

Adicionar evidence, source, category e review history sem quebrar o contrato mínimo.

## 10. Finance / FinOps

Entidades mínimas:

- CostEntry
- RevenueEntry
- Budget
- CostAllocation
- VendorService
- BillingSource
- FinancialSnapshot
- UnitEconomicsSnapshot

Dimensões mínimas:

- project
- service/vendor
- model
- API
- GPU/CPU
- storage
- research
- content generation
- agent/workflow
- software/service
- infrastructure
- period

Nunca tratar ROI como garantido. Guardar premissas e confidence/evidence.

## 11. Dependency Graph

Nós:

- PROJECT
- SERVICE
- DATA
- API
- AGENT
- SKILL
- MODEL
- INFRASTRUCTURE

Arestas versionadas com tipo, criticality, owner, evidence e health propagation.

Objetivos:

- detectar single points of failure;
- detectar chains de bloqueio;
- propagar impacto de falhas;
- suportar priorização do PMO/CEO AI.

## 12. Venture Factory

Pipeline obrigatório:

```text
IDEA
-> RESEARCH_REQUEST
-> MARKET ANALYSIS
-> TECHNICAL ANALYSIS
-> AUTOMATION ANALYSIS
-> UNIT ECONOMICS
-> RISK
-> CHEAP VALIDATION
-> GATE
-> BUILD | HOLD | REJECT
```

Gates permanentes:

- ~80–90%+ automação plausível após maturidade;
- não exigir abandono imediato do emprego atual;
- baixa presença física diária;
- delegável a IA/software/terceiros;
- unit economics positivo ou plausível;
- risco jurídico/financeiro controlável;
- validação barata antes de escala.

## 13. Fronteira com o Segundo Cérebro

O código atual possui Universal Knowledge Core dentro de `AI-Holding`. Pela arquitetura oficial:

- Holding mantém somente estado operacional e referências necessárias;
- knowledge entities, claims, evidence e relações duradouras pertencem ao Segundo Cérebro/Knowledge Factory;
- não apagar tabelas/dados existentes até concluir export/migration/reconciliation;
- criar adapter versionado e dual-read temporário somente se necessário;
- cortar escrita canônica na Holding após validação de migração;
- manter audit trail completo.

## 14. Segurança

Manter Defense in Depth e Zero Trust.

Obrigatório:

- least privilege
- RBAC/service identities
- short-lived credentials
- network segmentation/egress controls
- TLS/encryption at rest
- MFA quando aplicável
- rate limits
- audit logs
- secret broker/vault
- external content = untrusted
- prompt/tool injection defense
- SAST
- secret scanning
- dependency scanning
- SBOM
- license scanning
- container scanning
- vulnerability scanning

Security Test Lab deve cobrir:

- prompt injection
- tool injection
- secret exfiltration
- SQL injection
- command injection
- SSRF
- XSS
- CSRF
- path traversal
- webhook spoofing
- replay
- auth bypass
- tenant escape
- privilege escalation
- malicious files/dependencies
- API abuse
- rate-limit bypass

## 15. Ordem de implementação sem criar protótipos paralelos

1. congelar contratos e migração de estados;
2. ampliar Project Registry sem quebrar API atual;
3. criar Collector Registry + execution history;
4. criar Project Contract adapters;
5. criar Project Health Engine;
6. criar Risk Registry;
7. criar Finance/FinOps;
8. criar Dependency Graph global;
9. criar Resource Allocation;
10. operacionalizar Venture Factory;
11. formalizar CEO/PMO/Governance/Auditor sobre dados reais;
12. integrar Hermes;
13. integrar Research AI;
14. migrar Knowledge Core para adapter do Segundo Cérebro;
15. consolidar observabilidade/security posture;
16. executar Security Test Lab;
17. executar matriz E2E oficial;
18. corrigir todos os gaps;
19. somente então declarar Holding operacional.

## 16. E2E oficial

A Holding não é aceita enquanto não passar, com evidência persistida, pelos oito cenários:

1. `Como está a Holding?` retorna estado real coletado.
2. `Continue o AgroLog.` resolve trabalho, executa, testa, audita e atualiza estado.
3. collector falha -> health degrada -> alerta -> recuperação.
4. projeto declara completed sem evidência -> Auditor rejeita.
5. gasto relevante -> policy exige aprovação.
6. custo anormal -> FinOps detecta e abre investigação.
7. dependência crítica falha -> graph identifica impacto.
8. novo negócio -> Venture Factory executa pesquisa, unit economics, gates e decisão.

## 17. Definition of Done da Holding

A Holding somente pode receber status operacional final quando:

- registry reflete projetos reais;
- estado é coletado automaticamente;
- Project Health funciona;
- PMO usa dados reais;
- CEO AI prioriza com evidências;
- Governance/A0–A6 funcionam;
- Auditor valida entregas;
- Finance/FinOps mede custos;
- Risk Registry funciona;
- Venture Factory funciona;
- Dependency Graph funciona;
- integrações Hermes/Research/Segundo Cérebro funcionam;
- segurança e Security Test Lab passam;
- backups e restores são testados;
- observabilidade funciona;
- E2E oficial passa.

Até lá, o sistema pode estar parcialmente operacional, mas não deve se autodeclarar `COMPLETED`.