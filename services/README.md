# Services

Fronteiras de infraestrutura e execução da Holding. Cada serviço deve ter contrato explícito, identidade própria e menor privilégio.

- `agent_runtime/`: Agno AgentOS — agents, teams, workflows, scheduler, durable queue e HITL.
- `model_gateway/`: LiteLLM — aliases de modelos, routing, fallback, budgets, rate limits e custos. A política de roteamento usa aliases lógicos e mantém private workloads fail-closed.
- `coding_agents/`: OpenHands — Claude Code/Codex em workspaces isolados, branch/test/PR/CI.
- `observability/`: Langfuse — traces, custo, latência, retries, avaliações e falhas.
- `policy/`: autorização determinística, A0–A6 e gates de risco; nasce da lógica validada em `app/core`/`app/services`.
- `secrets/`: Infisical e ponte temporária com Secret Manager; agentes não recebem segredo bruto quando proxy/injeção for possível.
- `project_control/`: fronteira do estado operacional canônico de projetos, milestones, tarefas, runs, decisões, approvals e incidentes; a implementação validada permanece em `app/` durante a migração.
- `collectors/`: ingestão read-only do estado de AgentOS, PostgreSQL, GitHub/CI, LiteLLM, Langfuse, infraestrutura, logs, custos, filas e workflows para o Collector Registry.

Nenhum serviço deve ser duplicado por outro framework com a mesma responsabilidade sem ADR e evidência operacional.