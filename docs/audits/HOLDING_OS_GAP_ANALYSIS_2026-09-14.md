# Holding Digital / AI OS — Gap Analysis obrigatório

Data-base: 2026-09-14
Escopo auditado: `brunocapellari-dotcom/AI-Holding`, `main` em `5dc7e1f8604ad2e5708ed63afe3694610e2303b7` e migração arquitetural em `architecture/agentos-holding-os` / PR #41.

## Regra de evolução

Esta auditoria é **incremental e não destrutiva**. Componentes que já demonstraram funcionamento não devem ser substituídos por equivalentes novos sem acceptance gate, rollback e evidência de superioridade. A migração para AgentOS, LiteLLM, Infisical, Langfuse, OpenHands, MCP Gateway e Segundo Cérebro externo deve seguir padrão strangler: preservar o Control Plane, PostgreSQL, IAM/WIF, idempotência, policy A0–A6, migrations, CI, audit trail e jobs já validados até o novo caminho passar por testes equivalentes.

Status usados: **EXISTE**, **EXISTE PARCIALMENTE**, **NÃO EXISTE**, **QUEBRADO**, **DUPLICADO**, **OBSOLETO**.

## 1. Matriz da Fase 0

| Área | Status | Evidência atual | Gap principal |
| --- | --- | --- | --- |
| Arquitetura operacional | EXISTE PARCIALMENTE | FastAPI Control Plane + PostgreSQL + Cloud Run + documentos; PR #41 formaliza AI OS | Arquitetura oficial ainda não integralmente operacional/mergeada |
| Control Plane | EXISTE | Projects, milestones, criteria, tasks, runs, decisions, approvals, incidents, audit, executive summary | Expandir custo, collectors, segurança e estado de serviços |
| Hermes | EXISTE PARCIALMENTE | Agent seed + contrato em `apps/hermes` no PR #41 | Falta runtime, API executiva, contexto real e model routing |
| CEO IA | EXISTE PARCIALMENTE | Agent seed `CEO_IA` | Falta runtime, priorização baseada em evidência e acceptance |
| PMO IA | EXISTE | Registry, policy, claim transacional, Cloud Run worker, recurring execution e acceptance | Migrar gradualmente para AgentOS sem perder garantias |
| Governance AI | NÃO EXISTE | Apenas responsabilidades documentadas | Falta agente canônico, runtime, policies e avaliações |
| Risk AI | NÃO EXISTE | Risco existe como campo/policy, não como agente | Falta agente canônico e motor de risco operacional/financeiro/legal/técnico |
| Auditor AI | EXISTE PARCIALMENTE | `AUDITOR_IA`, permissões de conhecimento, docs | Falta runtime independente e regra produtor != auditor por modelo/agente |
| Security AI | NÃO EXISTE | Controles de segurança existem sem agente especializado | Falta agente canônico, detecção, incident triage e security acceptance |
| Architect AI | NÃO EXISTE | Arquitetura é documental/manual | Falta agente canônico e verificação de arquitetura transversal |
| Finance AI | NÃO EXISTE | Sem agente/camada financeira operacional | Falta custo, runway, ROI, monetização e budget telemetry |
| Knowledge IA legado | EXISTE / OBSOLETO COMO CANÔNICO | Rotas/tabelas/workers de knowledge atuais | Preservar para migração/auditoria; impedir canonicalização pela Holding |
| Agno AgentOS | EXISTE PARCIALMENTE | PR #41 adiciona runtime feature-gated com Postgres/queue/scheduler | `agents=[]`, `teams=[]`, `workflows=[]`; ainda não é runtime real da Holding |
| Fila durável | EXISTE PARCIALMENTE | Task/Run ledger atual é durável; AgentOS QueueConfig no PR #41 | Falta acceptance de fila AgentOS e cutover controlado |
| Scheduler/automações | EXISTE | GitHub Actions recorrente keyless para PMO/Knowledge | Migrar para scheduler AgentOS somente após aceitação; evitar duplicidade |
| LiteLLM | EXISTE PARCIALMENTE | Config baseline no PR #41 | `model_list` vazio; sem proxy implantado, aliases, budgets, routing ou health |
| vLLM / Llama | NÃO EXISTE | Nenhum runtime/model endpoint configurado | Falta capacidade local/remota autorizada atrás do LiteLLM |
| OpenHands | NÃO EXISTE | Apenas fronteira documental no PR #41 | Falta serviço, sandbox, workspace, branch/test/PR e policy gates |
| Claude Code / Codex workers | EXISTE PARCIALMENTE | Conceito/documentação e uso humano externo | Falta integração operacional via OpenHands/model/tool gateway |
| Docker MCP Gateway | NÃO EXISTE | Apenas arquitetura/documentação | Falta gateway, allowlists, profiles e tool-call audit |
| E2B/microVM | NÃO EXISTE | Apenas política alvo | Falta adapter e critérios de escalonamento de risco |
| Infisical | EXISTE PARCIALMENTE | Arquitetura alvo documentada | Secret Manager continua ativo; falta Agent Vault/machine identity/cutover |
| PostgreSQL | EXISTE | Cloud SQL PostgreSQL 16 privado, Alembic, backups/PITR | Falta restore test periódico e schemas/telemetria novos |
| Bancos analíticos por projeto | FORA DO NÚCLEO / PARCIAL | Control Plane referencia projetos; BigQuery é responsabilidade das unidades | Collectors devem registrar estado sem duplicar dados das unidades |
| APIs de projetos/tarefas/agentes/runs/incidentes/decisões | EXISTE | FastAPI `app/api/routes` | Falta collectors, costs, runtime-services, security state, Hermes |
| Collector Registry | NÃO EXISTE | Nenhum modelo/rota canônica | Implementar tabela, API, health/reporting e owners |
| Collectors PostgreSQL/Control Plane | NÃO EXISTE | Dados existem, coleta contínua não | Criar collector interno idempotente |
| Collector GitHub/CI | NÃO EXISTE | GitHub Actions existe, sem ingestão de estado no CP | Criar adapter read-only + freshness |
| Collector AgentOS | NÃO EXISTE | AgentOS ainda desativado | Criar após schema/runtime aceito |
| Collector LiteLLM/custos | NÃO EXISTE | Gateway ainda não operacional | Criar após proxy/DB do LiteLLM |
| Collector Langfuse | NÃO EXISTE | Langfuse ainda não operacional | Criar após observability service |
| Collector infraestrutura/logs | EXISTE PARCIALMENTE | GCP tem logs/métricas, CP não ingere saúde consolidada | Criar adapter de estado/custo/incidentes |
| Segundo Cérebro externo | EXISTE PARCIALMENTE | PR #41 estabelece fronteira/inbox; PR #40 desenvolve núcleo independente | Falta connector estável de consulta + entrega de evidência e acceptance |
| Autenticação | EXISTE | Cloud Run IAM, Google ID token verification, WIF | AgentOS auth/JWT ainda feature-gated |
| RBAC / permissões | EXISTE PARCIALMENTE | AgentPermission + binding por identidade + IAM | Falta escopo por projeto, tool-level grants e credencial efêmera |
| Zero Trust | EXISTE PARCIALMENTE | IAM, WIF, private DB, explicit agent permissions | Falta política uniforme entre novos serviços/gateways |
| Secrets fora do código | EXISTE | Secret Manager e WIF; sem provider keys commitadas | Migrar para Infisical sem expor segredo bruto |
| MFA | EXISTE PARCIALMENTE / EXTERNO | Depende da identidade humana Google/GitHub | Formalizar requisito e auditoria de configuração de conta |
| Criptografia em trânsito | EXISTE | Cloud Run HTTPS, Cloud SQL `sslmode=require`/encrypted | Validar novos serviços com TLS/mTLS conforme fronteira |
| Criptografia em repouso | EXISTE PARCIALMENTE | GCP managed encryption | Formalizar requisitos e tratamento de material restrito |
| Rotação de credenciais | EXISTE PARCIALMENTE | WIF elimina chaves estáticas em vários fluxos | Falta policy/telemetria de rotação para secrets restantes |
| Logs de aplicação | EXISTE | Cloud Logging + app logging | Falta correlação universal e política de retenção/WORM |
| Audit trail | EXISTE | `audit_events`, request IDs e gates | Falta imutabilidade externa e eventos de todos os novos gateways |
| Langfuse | NÃO EXISTE | Só alvo/config callback LiteLLM | Falta implantação, redaction e trace IDs |
| Prometheus/métricas | EXISTE | `/metrics` | Falta dashboards/SLOs/alert rules versionados |
| Rate limiting | NÃO EXISTE | Sem camada explícita | Implementar no gateway/API conforme identidade e rota |
| Segmentação de rede | EXISTE PARCIALMENTE | VPC, DB privado, private service networking | Egress dos agentes/tools ainda não tem política completa |
| Firewall/allowlists | EXISTE PARCIALMENTE | IAM e rede GCP base | Falta egress allowlist/tool domains e controle de MCP |
| Isolamento de agentes | EXISTE PARCIALMENTE | SAs distintas para workers | Falta sandbox/workspace/process/network isolation por tarefa |
| Input validation | EXISTE | Pydantic + constraints + ORM | Ampliar para payloads externos/webhooks/tools |
| Prompt injection protection | NÃO EXISTE | Sem gateway/guard dedicado | Criar policy de conteúdo/tool boundary e testes adversariais |
| Tool injection protection | NÃO EXISTE | MCP Gateway ainda ausente | Allowlist + schema validation + policy decision + audit |
| Dependency poisoning defense | EXISTE PARCIALMENTE | pip-audit, Trivy, pinned GitHub actions em partes | Falta lock/allowlist, provenance e testes de supply chain |
| Backups | EXISTE | Cloud SQL backups + PITR | Falta backup de novos stores e restore test |
| Restore test | NÃO EXISTE | Não há evidência automatizada | Criar job periódico em ambiente isolado |
| Disaster recovery | EXISTE PARCIALMENTE | Backups + IaC | Falta RTO/RPO, runbook e exercício comprovado |
| Login anômalo / privilege escalation alert | NÃO EXISTE | IAM logs existem, sem detector dedicado no repo | Criar regras/collector/security incident pipeline |
| Repeated-attempt blocking/session expiry/short tokens | EXISTE PARCIALMENTE | Cloud/IAM tokens são temporários | Falta controle de app/gateway/rate limit uniforme |
| SAST | EXISTE | Bandit + Ruff/mypy auxiliares | Incluir novas raízes e regras de supply chain |
| Dependency scanning | EXISTE | pip-audit + Trivy | Evoluir para lock/provenance |
| Secret scanning | NÃO EXISTE | Nenhum gate explícito versionado | Adicionar scanner no CI/pre-commit |
| SBOM | EXISTE | CycloneDX image SBOM | Manter artifact/provenance e política de retenção |
| Container scanning | EXISTE | Trivy HIGH/CRITICAL | Manter e estender a imagens dos novos serviços |
| License scanning | NÃO EXISTE | Sem gate | Adicionar allow/deny policy para dependências |
| DAST | NÃO EXISTE | Sem etapa dinâmica dedicada | Introduzir após endpoint de staging/preview seguro |
| Security Test Suite | NÃO EXISTE COMO SUÍTE ÚNICA | Existem testes auth/policy espalhados | Consolidar matriz adversarial e adicionar gaps solicitados |
| CI/CD | QUEBRADO NO ESTADO ATUAL | Workflow é completo, mas último run em main falhou antes de executar steps e deploy foi pulado | Diagnosticar infraestrutura do runner/workflow antes de declarar release saudável |
| Branch protection | NÃO EXISTE | `main` está sem proteção/status checks obrigatórios | Ativar ruleset/protection com quality requerido |
| Infraestrutura GCP | EXISTE | Cloud Run, Cloud SQL privado, VPC, Artifact Registry, Secret Manager, WIF/Terraform | Acrescentar novos serviços somente após acceptance |
| IaC | EXISTE | Terraform + non-destructive plan gate + prevent_destroy | Separar stacks gradualmente sem state move arriscado |
| Documentação | EXISTE PARCIALMENTE | arquitetura, segurança, runbooks, portfolio; PR #41 amplia | Gap Analysis e ADRs/cutover status precisam ser canônicos |
| Estrutura `/apps` | EXISTE PARCIALMENTE | PR #41 cria Hermes/Control Plane | Hermes ainda só contrato |
| Estrutura `/services` | EXISTE PARCIALMENTE | PR #41 cria runtime/model/coding/policy/secrets/observability | Faltam `project_control` e `collectors` como fronteiras explícitas |
| Estrutura `/agents` | EXISTE PARCIALMENTE | PR #41 cria raiz documental | Faltam contratos separados para todos os agentes oficiais |
| Estrutura `/evaluation` | NÃO EXISTE | — | Criar avaliações operacionais e de segurança |
| Custos/runway/ROI | NÃO EXISTE | — | Finance AI + cost collectors + budget data model |
| Estado real de projeto automatizado | EXISTE PARCIALMENTE | CP é fonte de verdade, mas depende de eventos internos | GitHub/CI/infra/cost collectors faltam para fechar o loop |

## 2. Itens ausentes/quebrados — impacto e implementação

| Item | Impacto | Prioridade | Dependências | Implementação segura | Teste obrigatório |
| --- | --- | --- | --- | --- | --- |
| CI atual não inicia quality job | Bloqueia confiança em qualquer merge/deploy | P0 | GitHub Actions | diagnosticar runner/workflow sem desligar gates | workflow completo verde antes de merge |
| Branch protection | Permite mudança em `main` sem gate | P0 | GitHub repo settings | ruleset exigindo PR + `quality`; limitar bypass | tentativa de push/merge sem check deve falhar |
| Collector Registry | Holding não conhece freshness/saúde das fontes | P0 | PostgreSQL/Alembic | modelo + migration + API + audit + health reports | migration round-trip, CRUD/auth, stale/failure transitions |
| Missing official agents | Cadeia oficial incompleta | P0 | Agent Registry/bootstrap | adicionar Governance, Risk, Security, Architect, Finance como disabled por padrão | bootstrap idempotente + identity drift |
| AgentOS sem agentes/workflows | Runtime alvo não executa Holding real | P1 | PR #41, Postgres schema, auth | registrar agentes/teams/workflows gradualmente atrás de feature gate | parity acceptance contra PMO atual |
| LiteLLM vazio | Sem gateway real ou governança de modelos | P1 | secret store, providers | logical aliases + budgets + rate limit + health; provider creds fora Git | routing/fallback/budget/fail-closed |
| Llama/vLLM | Rotina local/privada sem backend preferencial | P1 | hardware/endpoint autorizado | endpoint vLLM atrás de alias LiteLLM; remoto controlado se necessário | privacy/routing/latency/failure fallback |
| Hermes runtime | Owner não tem interface persistente real | P1 | Control Plane, LiteLLM, Second Brain connector | API/agent que só lê estado canônico e cria trabalho via policy | factual-state tests, no invented progress |
| Governance/Risk/Audit/Security runtime | Falta supervisão independente contínua | P1 | AgentOS, policies, telemetry | workflows separados e auditor diferente do produtor | cross-agent independence + deny tests |
| Project Control service boundary | Lógica fica dispersa | P1 | Control Plane | extrair contratos sem reescrever APIs | compatibility tests |
| GitHub/CI collector | CP não sabe código/checks reais | P1 | GitHub App/token read-only | collector incremental com ETag/cursor/freshness | replay/idempotency/rate-limit/failure |
| Infra/cost collector | Hermes/Finance não veem custo/saúde | P1 | GCP APIs/read identities | read-only adapters + normalized snapshots | least privilege + freshness + cost attribution |
| Langfuse | Sem observabilidade de IA central | P1 | LiteLLM/AgentOS | service + redaction + trace IDs | no-secret trace, correlation, outage tolerance |
| Infisical | Secret Manager segue ponte | P1 | machine identities, deployment | parallel read/validation then cutover; no bulk secret exposure | rotation/revocation/no-plaintext logs |
| Docker MCP Gateway | Tool authorization não tem enforcement central | P1 | Policy, Infisical | tool allowlist, scoped profiles, audit, egress policy | forbidden tool/tool injection/credential scope |
| Security Test Suite | Risco sem prova regressiva unificada | P1 | auth/policy/gateway | suíte adversarial versionada | todos os casos solicitados no briefing |
| Secret scanning | Possível vazamento em commits | P1 | CI | scanner fail-closed + allowlist justificada | synthetic secret fixture deve bloquear |
| License scanning | Dependência incompatível pode entrar | P2 | CI/SBOM | policy allow/deny + artifact report | pacote de licença negada deve falhar |
| Rate limiting | DoS/abuso sem controle app-level | P1 | gateway/API identity | limites por identidade/rota + backoff | 429/retry-after/isolamento entre identidades |
| Project isolation | Serviço autorizado pode cruzar projeto | P1 | RBAC + task/project context | project-scoped grants/claims | cross-project read/write deny |
| Prompt/tool injection | Agentes podem ser induzidos a exceder autoridade | P1 | MCP/Policy/model gateway | treat external content as untrusted; structured tool contracts; deny by policy | adversarial prompts cannot widen tools/credentials |
| Restore test/DR | Backup pode ser inútil sem prova | P1 | Cloud SQL backup, isolated env | restore periódico não destrutivo + integrity checks + RTO/RPO | restore + migration + checksums/readiness |
| Immutable audit export | DB admin pode alterar audit trail | P2 | storage/log sink | append-only sink with retention lock where appropriate | tamper/retention verification |
| Anomaly/security alerts | Incidente só aparece após dano | P1 | cloud audit logs/collectors | rules for auth anomaly, privilege change, repeated failure | synthetic events create incident |
| OpenHands coding service | Coding agents sem execução padronizada | P2 | sandbox, GitHub, policy | isolated workspace, no merge/prod by default | malicious repo/tool/egress tests |
| E2B/microVM | Untrusted code lacks stronger isolation | P2 | policy classification | adapter invoked only for high-risk/untrusted code | escape/network/secret-isolation tests |
| DAST | Falhas runtime HTTP podem escapar ao SAST | P2 | staging/preview | authenticated scanner against disposable nonprod | auth bypass, injection and headers checks |

## 3. Duplicações e obsolescência

- O **Knowledge Core dentro da Holding** é legado de transição. Não apagar. Novas promoções para conhecimento canônico devem ser bloqueadas; a fonte canônica é o Segundo Cérebro externo.
- O **Cloud Scheduler antigo** e abordagens antigas de recorrência são obsoletos quando duplicarem GitHub WIF/AgentOS. Nenhum segundo scheduler deve ficar ativo simultaneamente sem justificativa.
- PRs antigos que implementam funções já presentes em `main` devem ser classificados como duplicados/obsoletos e fechados somente após verificação de que não contêm mudança exclusiva necessária.
- Não adicionar LangGraph, CrewAI, AutoGen, ADK ou outro runtime geral ao lado do AgentOS sem ADR e requisito comprovado.
- Não adicionar Phoenix enquanto Langfuse for suficiente.

## 4. Ordem segura de fechamento dos gaps

1. Recuperar CI e manter todos os gates existentes.
2. Registrar este Gap Analysis como baseline versionado.
3. Completar Agent Registry oficial sem ativar permissões automaticamente.
4. Criar Collector Registry + collector interno do Control Plane.
5. Adicionar adapters read-only GitHub/CI e infraestrutura/custos.
6. Consolidar Security Test Suite e gaps de supply-chain.
7. Tornar LiteLLM operacional com aliases/budgets e depois adicionar Llama/vLLM.
8. Instrumentar Langfuse com redaction.
9. Migrar secrets para Infisical por leitura paralela/cutover controlado.
10. Ativar AgentOS primeiro em modo controlado, depois mover PMO/agents com parity acceptance.
11. Implementar Hermes real sobre estado canônico + model gateway + connector do Segundo Cérebro.
12. Ativar CEO/Governance/Risk/Auditor/Security/Architect/Finance com permissões mínimas e acceptance próprio.
13. Implantar MCP Gateway/OpenHands/sandbox e somente então coding autonomy ampliada.
14. Provar backup restore/DR e completar observability/security SLOs.

## 5. Critério de operacionalidade

A Holding só pode ser marcada `OPERACIONAL` quando houver evidência objetiva de que:

1. estado de projeto é canônico e atualizado automaticamente;
2. Collector Registry reporta freshness/falhas;
3. incidentes são criados para falhas materiais;
4. CEO/PMO conseguem priorizar e despachar trabalho dentro da policy;
5. workers executam com identidade mínima e audit trail;
6. Hermes apresenta somente estado comprovado;
7. Segundo Cérebro é consultado por contrato externo e recebe evidência de volta;
8. Auditor usa contexto/modelo independente do produtor quando aplicável;
9. secrets e tools ficam atrás de autorização determinística e escopo mínimo;
10. restore/DR foi testado;
11. CI/CD e production acceptance estão verdes;
12. nenhum scheduler/runtime duplicado executa a mesma responsabilidade.

Até lá, o status correto é **MIGRAÇÃO CONTROLADA / PARCIALMENTE OPERACIONAL**, não “100% operacional”.
