# Policy Service

Fronteira determinística de autorização e risco. A lógica A0–A6 e as regras já validadas em `app/core/authorization.py` e `app/services/policy.py` são a base a preservar e extrair gradualmente para este serviço.

Decisão de IA não concede permissão. O Policy Service avalia ator/agent, projeto, recurso, ação, autonomia, risco, aprovação humana, escopo temporal e evidência necessária antes da execução.

OpenFGA é reserva futura: entra somente se as relações agente↔recurso↔projeto↔período deixarem de ser expressáveis com clareza e auditabilidade na política atual.
