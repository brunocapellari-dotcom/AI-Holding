# Collectors

Camada de coleta do estado operacional da Holding. Collectors são somente leitores das fontes de origem e escritores do contrato normalizado do Control Plane; não tomam decisões nem alteram a fonte observada.

Fontes previstas: Control Plane/PostgreSQL, AgentOS, GitHub, CI/CD, LiteLLM, Langfuse, infraestrutura, logs, custos, filas e workflows.

Todo collector deve possuir registro no Collector Registry com `collector_id`, fonte, tipo, frequência, última coleta, status, latência, falhas, responsável e dados produzidos. Falhas devem ser explícitas; freshness não pode ser inferida de dado antigo.

Credenciais são read-only sempre que tecnicamente possível. O collector não recebe privilégio administrativo para facilitar integração.