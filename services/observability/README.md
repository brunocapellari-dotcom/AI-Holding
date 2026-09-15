# Observability — Langfuse

Camada central de observabilidade de IA. Não substitui Cloud Logging/Monitoring para infraestrutura; complementa-os com telemetria de execução de modelos e agentes.

Dimensões mínimas: project_id, agent_id, task_id, run_id, workflow, alias/modelo, provider, tokens, custo, latência, retry, fallback, policy outcome, erro e avaliação.

Regras de segurança:
- redigir segredos e dados restritos antes do trace;
- prompts completos só são registrados quando a política de dados permitir;
- traces não concedem autorização nem se tornam fonte operacional de verdade;
- Phoenix não será instalado em paralelo na fase inicial.
