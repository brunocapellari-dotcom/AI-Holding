# Workflows

Workflows de negócio serão executados pelo Agno AgentOS. Esta pasta contém definições e contratos versionados; estado de execução pertence ao PostgreSQL/AgentOS.

Fluxos prioritários:

1. `owner-command`: Hermes → estruturação → Policy → CEO/PMO → tarefa(s) → acompanhamento → resposta executiva.
2. `project-work`: seleção de tarefa elegível → execução → evidência → review/auditoria → conclusão ou incidente.
3. `coding-work`: PMO → OpenHands → Claude/Codex → branch → testes → PR → CI → auditoria → merge por política.
4. `human-approval`: pausa durável → “Precisa de você” → decisão registrada → retomada idempotente.
5. `second-brain-exchange`: contexto validado entra; resultado/evidência sai como candidato para validação externa.

Todo workflow deve possuir idempotency key, política de retry, timeout, estados terminais, evidência de sucesso e comportamento fail-closed para risco material.
