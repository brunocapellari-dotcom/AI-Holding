# Model Gateway — LiteLLM

Único caminho padrão da Holding para modelos remotos e locais.

O gateway mantém aliases lógicos, routing, retry/fallback, budgets, rate limits, spend e permissões por projeto/agente. Chaves de provedores pertencem ao serviço e serão injetadas pelo Infisical; agentes recebem somente credencial virtual limitada do gateway.

Regras:
- budgets que limitam gasto exigem PostgreSQL; não operar budget crítico em modo DB-less;
- cada chamada carrega tags `project_id`, `agent_id`, `task_id` e `run_id` quando disponíveis;
- fallback nunca pode aumentar autoridade nem ignorar restrição de dados;
- modelos locais/zero-cost podem ser fallback econômico quando a política da tarefa permitir;
- Langfuse recebe telemetria do gateway; segredos e conteúdo restrito são redigidos antes do envio;
- nenhum código de domínio deve depender de um nome físico de modelo.

`litellm.config.yaml` contém somente configuração não secreta. Modelos, chaves e budgets de produção são provisionados por identidade e configuração controlada, não commitados no GitHub.
